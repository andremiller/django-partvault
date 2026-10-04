import type { FieldErrors, Session } from '../types/api'

export type ErrorKind = 'authentication' | 'csrf' | 'permission' | 'not-found' | 'validation' | 'network' | 'server'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly kind: ErrorKind,
    public readonly fields: FieldErrors = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

let csrfToken: string | null = null
export function setCsrfToken(token: string | null) { csrfToken = token }

function transportError(error: unknown): never {
  if (error instanceof ApiError || (error instanceof DOMException && error.name === 'AbortError')) throw error
  throw new ApiError('Could not reach the server. Check your connection.', 0, 'network')
}

function sameOriginUrl(path: string): URL {
  const url = new URL(path, window.location.origin)
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/v1/') || url.username || url.password) {
    throw new ApiError('This request does not point to the inventory API.', 0, 'validation')
  }
  return url
}

function normalizeError(status: number, payload: unknown): ApiError {
  const fields: FieldErrors = {}
  let detail = ''
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    for (const [key, value] of Object.entries(payload)) {
      if (key === 'detail' && typeof value === 'string') detail = value
      else if (Array.isArray(value) && value.every((entry) => typeof entry === 'string')) fields[key] = value
    }
  }
  const kind: ErrorKind = status === 401 ? 'authentication'
    : status === 403 ? (/csrf/i.test(detail) ? 'csrf' : /authentication credentials/i.test(detail) ? 'authentication' : 'permission')
      : status === 404 ? 'not-found' : status === 400 ? 'validation' : 'server'
  const fallback = status === 413 ? 'The upload is too large for the server.'
    : status === 404 ? 'This record is unavailable.'
      : status === 403 ? 'This action is not permitted. Refresh your session and try again.'
        : status >= 500 ? 'The server could not complete the request. Try again later.'
          : `The request failed (HTTP ${status}).`
  return new ApiError(detail || fields.non_field_errors?.join(' ') || fallback, status, kind, fields)
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers = new Headers({ Accept: 'application/json' })
  if (method !== 'GET') {
    if (!csrfToken) throw new ApiError('Refresh your session before saving.', 403, 'csrf')
    headers.set('X-CSRFToken', csrfToken)
  }
  let body: BodyInit | undefined
  if (options.body instanceof FormData) body = options.body
  else if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }
  let response: Response
  try {
    response = await fetch(sameOriginUrl(path), { method, headers, body, signal: options.signal, credentials: 'same-origin', redirect: 'error' })
  } catch (error) {
    transportError(error)
  }
  let text: string
  try { text = await response.text() } catch (error) { transportError(error) }
  let payload: unknown = null
  try { payload = text ? JSON.parse(text) : null } catch { /* Proxy errors can be HTML. */ }
  if (!response.ok) throw normalizeError(response.status, payload)
  if (response.status === 204) return undefined as T
  if (payload === null) throw new ApiError('The server returned an unexpected response.', response.status, 'server')
  return payload as T
}

export async function bootstrapSession(signal?: AbortSignal): Promise<Session> {
  const session = await apiRequest<Session>('/api/v1/session/', { signal })
  if (typeof session.csrf_token !== 'string' || !session.csrf_token) {
    throw new ApiError('The session response is incomplete. Please refresh.', 200, 'server')
  }
  return session
}

export async function apiDownload(path: string, signal?: AbortSignal): Promise<Blob> {
  let response: Response
  try {
    response = await fetch(sameOriginUrl(path), {
      credentials: 'same-origin', redirect: 'error', signal,
      headers: { Accept: 'application/octet-stream, application/json' },
    })
  } catch (error) {
    transportError(error)
  }
  if (!response.ok) {
    let payload: unknown = null
    try { payload = await response.json() } catch { /* Proxy errors may be HTML. */ }
    throw normalizeError(response.status, payload)
  }
  try { return await response.blob() } catch (error) { transportError(error) }
}

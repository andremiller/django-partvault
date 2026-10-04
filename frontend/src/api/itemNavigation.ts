// Return context is navigation only, never an authorization decision.
export function itemBrowserReturn(candidate: unknown): string | null {
  if (typeof candidate !== 'string' || !candidate.startsWith('/app/items') || /[\\\r\n]/.test(candidate)) return null
  try {
    const url = new URL(candidate, window.location.origin)
    if (url.origin !== window.location.origin || !/^\/app\/items(?:\/[1-9]\d*)?\/$/.test(url.pathname)) return null
    return url.pathname.slice(4) + url.search
  } catch { return null }
}
export function itemRoute(id: number, browserPath: string) {
  return { path: `/item/${id}/`, query: { return: '/app' + browserPath } }
}
export function safeExternalLink(value: string): string | null {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}
export function protectedMediaPath(value: string | null, kind: 'image' | 'document'): string | null {
  if (!value) return null
  try {
    const url = new URL(value, window.location.origin)
    const pattern = kind === 'image' ? /^\/image\/[1-9]\d*(?:\/[1-9]\d*)?\/$/ : /^\/document\/[1-9]\d*\/$/
    return url.origin === window.location.origin && pattern.test(url.pathname) && !url.search && !url.hash ? url.pathname : null
  } catch { return null }
}

export function safeReturnPath(candidate = '/app/'): string {
  try {
    if (!candidate.startsWith('/') || candidate.startsWith('//') || /[\\\r\n]/.test(candidate)) return '/app/'
    const url = new URL(candidate, window.location.origin)
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/app/')) return '/app/'
    return url.pathname + url.search + url.hash
  } catch { return '/app/' }
}

export function authUrl(route: 'login' | 'signup', next?: string): string {
  return `/${route}/?${new URLSearchParams({ next: safeReturnPath(next) })}`
}

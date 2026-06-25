const DEFAULT_API_BASE_URL = '/api/v1'

function resolveBaseUrl(baseUrl: string) {
  return new URL(baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`, window.location.origin)
}

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL) as string

export function resolveApiUrl(path: string) {
  return new URL(path.replace(/^\//, ''), resolveBaseUrl(API_BASE_URL)).toString()
}

export function resolveHealthUrl() {
  return new URL('/health', resolveBaseUrl(API_BASE_URL)).toString()
}

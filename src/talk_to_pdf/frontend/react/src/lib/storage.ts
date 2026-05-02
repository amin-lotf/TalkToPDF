const TOKEN_STORAGE_KEY = 'talk-to-pdf-access-token'

export function readStoredToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function writeStoredToken(token: string) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

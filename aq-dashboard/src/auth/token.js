const TOKEN_KEY = 'aq_access_token'

// ─── token store ──────────────────────────────────────────────
export function getToken()   { return sessionStorage.getItem(TOKEN_KEY) }
export function setToken(t)  { sessionStorage.setItem(TOKEN_KEY, t)     }
export function clearToken() { sessionStorage.removeItem(TOKEN_KEY)     }

// ─── 401 callback slot ────────────────────────────────────────
// The fetch interceptor calls this whenever it sees a 401 from our API.
// App.jsx sets it on mount and clears it on unmount.
let _onUnauthorized = null

export function setOnUnauthorized(fn) { _onUnauthorized = fn }
export function getOnUnauthorized()   { return _onUnauthorized }

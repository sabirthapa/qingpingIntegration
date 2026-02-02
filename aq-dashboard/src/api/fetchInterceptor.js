import { getToken, clearToken, getOnUnauthorized } from '../auth/token.js'

// Read from environment variable with fallback to hardcoded default.
// The app continues to work even if .env is missing.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ou1jc1tszb.execute-api.us-west-1.amazonaws.com/dev'

// Keep a direct reference to the real fetch before we overwrite it.
// cognito.js imports this so its Cognito call never hits the interceptor.
export const originalFetch = window.fetch.bind(window)

/**
 * Install the interceptor.  Call once, before any component mounts.
 *
 *   • Adds  Authorization: Bearer <token>  to every request whose URL
 *     starts with API_BASE_URL.
 *   • On a 401 from API_BASE_URL: clears the token and invokes the
 *     onUnauthorized callback (wired by App.jsx) so the UI resets to login.
 */
export function installFetchInterceptor() {
  window.fetch = async function (input, options = {}) {
    const url      = typeof input === 'string' ? input : (input && input.url) || ''
    const isOurAPI = url.startsWith(API_BASE_URL)

    if (isOurAPI) {
      const token = getToken()
      if (token) {
        options.headers = {
          ...(options.headers || {}),
          Authorization: `Bearer ${token}`,
        }
      }
    }

    const response = await originalFetch(input, options)

    if (isOurAPI && response.status === 401) {
      clearToken()
      const cb = getOnUnauthorized()
      if (cb) cb()
    }

    return response
  }
}

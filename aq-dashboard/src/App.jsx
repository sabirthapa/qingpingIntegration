import { useState, useEffect, useCallback } from 'react'

import { getToken, clearToken, setOnUnauthorized } from './auth/token.js'
import LoginPage                                   from './components/LoginPage.jsx'
import AirQualityDashboard                         from './components/AirQualityDashboard.jsx'
import ErrorBoundary                               from './components/ErrorBoundary.jsx'

export default function App() {
  // false = not authenticated; truthy string = authenticated
  const [accessToken, setAccessToken] = useState(() => getToken() || false)

  // Wire the interceptor's 401 callback to this component's state.
  // Any 401 from API_BASE_URL will land here and drop us back to login.
  useEffect(() => {
    setOnUnauthorized(() => setAccessToken(false))
    return () => setOnUnauthorized(null)
  }, [])

  const handleLoginSuccess = useCallback(() => {
    // Token was already written to sessionStorage by LoginPage;
    // just re-read it so React re-renders the dashboard.
    setAccessToken(getToken())
  }, [])

  const handleLogout = useCallback(() => {
    clearToken()
    setAccessToken(false)
  }, [])

  // ── auth gate ─────────────────────────────────────────────
  if (!accessToken) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <ErrorBoundary>
      <AirQualityDashboard onLogout={handleLogout} />
    </ErrorBoundary>
  )
}

import { useState } from 'react'
import { Wind, Mail, Lock, LogIn, AlertCircle } from 'lucide-react'

import { cognitoLogin } from '../auth/cognito.js'
import { setToken }      from '../auth/token.js'

// ── small inline alert (only error variant is used on this page) ─
function LoginAlert({ children }) {
  return (
    <div className="px-4 py-3 rounded-lg border bg-red-50 border-red-200 text-red-800 mb-4 flex items-start gap-2 animate-fadeIn">
      <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
      <div className="flex-1">{children}</div>
    </div>
  )
}

export default function LoginPage({ onLoginSuccess }) {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState(null)
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const result = await cognitoLogin(email, password)
      setToken(result.AccessToken)
      // Token is in sessionStorage; tell App to re-render the dashboard.
      // (No reload needed — Tailwind classes are baked in at build time.)
      onLoginSuccess()
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* ── card ── */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden animate-fadeIn">

          {/* gradient header — same palette as dashboard cards */}
          <div className="bg-gradient-to-br from-blue-600 to-cyan-600 px-8 py-10 text-center">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Wind className="w-9 h-9 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Air Quality Automation</h1>
            <p className="text-blue-100 text-sm mt-1">Sign in to access your dashboard</p>
          </div>

          {/* form */}
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            {error && <LoginAlert>{error}</LoginAlert>}

            {/* email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <Mail className="w-5 h-5 text-gray-400" />
                </div>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <Lock className="w-5 h-5 text-gray-400" />
                </div>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                />
              </div>
            </div>

            {/* submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-6 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Sign In
                </>
              )}
            </button>
          </form>
        </div>

        {/* footer note */}
        <p className="text-center text-xs text-gray-500 mt-6">
          Secured with Amazon Cognito · Session expires on page reload
        </p>
      </div>
    </div>
  )
}

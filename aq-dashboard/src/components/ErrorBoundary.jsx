import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Dashboard error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-red-200 max-w-md w-full overflow-hidden">
            <div className="bg-gradient-to-br from-red-500 to-pink-500 px-8 py-6 text-center">
              <h2 className="text-xl font-bold text-white">Something went wrong</h2>
              <p className="text-red-100 text-sm mt-1">The dashboard failed to load</p>
            </div>
            <div className="p-8 space-y-4 text-center">
              <p className="text-sm text-gray-600 font-mono break-all">
                {this.state.error.message}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-all duration-200 shadow-md"
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

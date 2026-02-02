import React        from 'react'
import { createRoot } from 'react-dom/client'

import './index.css'
import { installFetchInterceptor } from './api/fetchInterceptor.js'
import App                          from './App.jsx'

// Install the Bearer-token interceptor once, before any component mounts.
// This guarantees every fetch() call made by any component already goes
// through the wrapper — including the very first API call on mount.
installFetchInterceptor()

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

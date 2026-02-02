import { useState, useEffect } from 'react'
import {
  Wind, Activity, Link as LinkIcon, RefreshCw,
  Download, LogOut, AlertCircle, CheckCircle,
} from 'lucide-react'

import { api, getDefaultDateRange } from '../api/api.js'
import { API_BASE_URL }             from '../api/fetchInterceptor.js'
import SensorCard                   from './SensorCard.jsx'
import MappingCard                  from './MappingCard.jsx'

function Alert({ type = 'info', children }) {
  const styles = {
    error:   'bg-red-50 border-red-200 text-red-800',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    info:    'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  }
  const Icon = type === 'error' ? AlertCircle : type === 'success' ? CheckCircle : null

  return (
    <div className={`px-4 py-3 rounded-lg border ${styles[type]} mb-4 flex items-start gap-2 animate-fadeIn`}>
      {Icon && <Icon className="w-5 h-5 mt-0.5 flex-shrink-0" />}
      <div className="flex-1">{children}</div>
    </div>
  )
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
    </div>
  )
}

// Dashboard 
export default function AirQualityDashboard({ onLogout }) {
  const [currentView,    setCurrentView]    = useState('devices')
  const userId                             = 'qingping_shared'
  const [devices,        setDevices]        = useState([])
  const [mappings,       setMappings]       = useState([])
  const [tuyaDevices,    setTuyaDevices]    = useState([])
  const [loading,        setLoading]        = useState(false)
  const [tuyaLoading,    setTuyaLoading]    = useState(false)
  const [error,          setError]          = useState(null)
  const [success,        setSuccess]        = useState(null)
  const [mapForm,        setMapForm]        = useState({ sensorMac: '', tuyaDeviceId: '', enabled: true })
  const [showMapForm,    setShowMapForm]    = useState(false)
  const [csvForm,        setCsvForm]        = useState({ sensorMac: '', sensorName: '', startDate: '', endDate: '' })
  const [showCsvForm,    setShowCsvForm]    = useState(false)
  const [csvDownloading, setCsvDownloading] = useState(false)

  // ── data loaders ──────────────────────────────────────────
  useEffect(() => {
    if (currentView === 'devices') { loadDevices(); loadMappings() }
    else                            { loadMappings() }
  }, [currentView]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadDevices = async () => {
    setLoading(true); setError(null)
    try   { const d = await api.listDevices(userId);  setDevices(d.devices || [])  }
    catch (e) { setError(`Failed to load devices: ${e.message}`) }
    finally   { setLoading(false) }
  }

  const loadMappings = async () => {
    setLoading(true); setError(null)
    try   { const d = await api.listMappings(userId); setMappings(d.mappings || []) }
    catch (e) { setError(`Failed to load mappings: ${e.message}`); setMappings([]) }
    finally   { setLoading(false) }
  }

  const loadTuyaDevices = async () => {
    setTuyaLoading(true); setError(null)
    try   { const d = await api.listTuyaDevices(); setTuyaDevices(d.devices || []) }
    catch (e) { setError(`Failed to load Tuya devices: ${e.message}`); setTuyaDevices([]) }
    finally   { setTuyaLoading(false) }
  }

  // mapping handlers
  const handleCreateMapping = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null); setSuccess(null)
    try {
      await api.createMapping(userId, mapForm.sensorMac, mapForm.tuyaDeviceId, mapForm.enabled)
      setSuccess('Mapping created successfully!')
      setShowMapForm(false)
      setMapForm({ sensorMac: '', tuyaDeviceId: '', enabled: true })
      loadDevices()
      loadMappings()
    } catch (err) { setError(`Failed to create mapping: ${err.message}`) }
    finally        { setLoading(false) }
  }

  const handleToggleMapping = async (m) => {
    try {
      await api.toggleMapping(userId, m.sensor_mac, m.tuya_device_id, !m.enabled)
      setSuccess(`Mapping ${!m.enabled ? 'enabled' : 'disabled'} successfully!`)
      loadMappings()
    } catch (e) { setError(`Failed to toggle mapping: ${e.message}`) }
  }

  const handleDeleteMapping = async (mac) => {
    try {
      await api.deleteMapping(mac)
      setSuccess('Mapping deleted successfully!')
      loadMappings()
    } catch (e) { setError(`Failed to delete mapping: ${e.message}`) }
  }

  //  modal openers
  const openMapForm = (dev) => {
    setMapForm({ sensorMac: dev.sensor_mac, tuyaDeviceId: '', enabled: true })
    setShowMapForm(true)
    setError(null); setSuccess(null)
    loadTuyaDevices()
  }

  const openCsvForm = (dev) => {
    const { start, end } = getDefaultDateRange()
    setCsvForm({
      sensorMac:  dev.sensor_mac,
      sensorName: dev.device_name || dev.product?.en_name || 'Air Monitor',
      startDate:  start,
      endDate:    end,
    })
    setShowCsvForm(true)
    setError(null); setSuccess(null)
  }

  // CSV download
  const handleDownloadCSV = async (e) => {
    e.preventDefault()
    if (!csvForm.startDate || !csvForm.endDate) { setError('Please select both start and end dates'); return }
    if (csvForm.startDate > csvForm.endDate)    { setError('Start date must be before or equal to end date'); return }

    setCsvDownloading(true); setError(null); setSuccess(null)

    try {
      const url = (
        `${API_BASE_URL}/download/csv` +
        `?sensor_mac=${encodeURIComponent(csvForm.sensorMac)}` +
        `&start_time=${csvForm.startDate}` +
        `&end_time=${csvForm.endDate}`
      )
      const response = await fetch(url)

      if (!response.ok) {
        const ct = response.headers.get('content-type')
        if (ct && ct.includes('application/json')) {
          const ed = await response.json()
          throw new Error(ed.message || `Server error: ${response.status}`)
        }
        throw new Error((await response.text()) || `Server returned status ${response.status}`)
      }

      const ct = response.headers.get('content-type')
      if (!ct || (!ct.includes('text/csv') && !ct.includes('application/csv'))) {
        throw new Error('Server did not return a CSV file. Got: ' + ct)
      }

      const blob    = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const a       = document.createElement('a')
      a.style.display = 'none'
      a.href          = blobUrl
      a.download      = `sensor_${csvForm.sensorMac}_${csvForm.startDate}_${csvForm.endDate}.csv`
      document.body.appendChild(a)
      a.click()
      setTimeout(() => { window.URL.revokeObjectURL(blobUrl); document.body.removeChild(a) }, 100)

      setSuccess('CSV downloaded successfully!')
      setShowCsvForm(false)
    } catch (err) {
      console.error('CSV download error:', err)
      setError(`Failed to download CSV: ${err.message}`)
    } finally {
      setCsvDownloading(false)
    }
  }

  const hasMappingForDevice = (mac) => mappings.some((m) => m.sensor_mac === mac)

  //  render
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50">

      {/* HEADER */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">

            {/* left: logo + title */}
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl flex items-center justify-center shadow-lg">
                <Wind className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                  Air Quality Automation
                </h1>
                <p className="text-sm text-gray-600 font-medium">Multi-Sensor Control System</p>
              </div>
            </div>

            {/* right: badge + logout */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg border border-blue-200">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-sm font-mono text-blue-900">qingping_shared</span>
              </div>
              <button
                onClick={onLogout}
                title="Sign out"
                className="p-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 border border-gray-200 hover:border-red-200 transition-all duration-200"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* NAV */}
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1">
            {[
              { id: 'devices',  label: 'Devices',  Icon: Activity },
              { id: 'mappings', label: 'Mappings', Icon: LinkIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => { setCurrentView(tab.id); setError(null); setSuccess(null) }}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-all duration-200 border-b-2 ${
                  currentView === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                }`}
              >
                <tab.Icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/*  MAIN  */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error   && <Alert type="error"  >{error}  </Alert>}
        {success && <Alert type="success">{success}</Alert>}

        {/*  Devices view  */}
        {currentView === 'devices' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Your Devices</h2>
              <button
                onClick={loadDevices}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-200 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {loading ? (
              <LoadingSpinner />
            ) : devices.length === 0 ? (
              <div className="text-center py-16 bg-white rounded-xl shadow-sm border border-gray-200">
                <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Devices Found</h3>
                <p className="text-gray-600">Make sure sensors are registered to the qingping_shared account.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {devices.map((dev) => (
                  <SensorCard
                    key={dev.sensor_mac}
                    device={dev}
                    onMapToPug={openMapForm}
                    onDownloadCSV={openCsvForm}
                    hasMappingExisting={hasMappingForDevice(dev.sensor_mac)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/*  Mappings view  */}
        {currentView === 'mappings' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Sensor-Plug Mappings</h2>
              <button
                onClick={loadMappings}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all duration-200 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {loading ? (
              <LoadingSpinner />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {mappings.map((m) => (
                  <MappingCard
                    key={m.sensor_mac}
                    mapping={m}
                    onToggle={handleToggleMapping}
                    onDelete={handleDeleteMapping}
                  />
                ))}
              </div>
            )}

            {!loading && mappings.length === 0 && (
              <div className="text-center py-16 bg-white rounded-xl shadow-sm border border-gray-200">
                <LinkIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Mappings Found</h3>
                <p className="text-gray-600 mb-6">Create sensor-to-plug mappings from the Devices page</p>
                <button
                  onClick={() => setCurrentView('devices')}
                  className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all duration-200"
                >
                  Go to Devices
                </button>
              </div>
            )}
          </div>
        )}

        {/*  MAP-TO-PLUG MODAL  */}
        {showMapForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="bg-gradient-to-br from-purple-600 to-pink-600 px-8 py-6">
                <h2 className="text-2xl font-bold text-white mb-2">Map Sensor to Plug</h2>
                <p className="text-purple-100">Create automation mapping for air quality control</p>
              </div>

              <form onSubmit={handleCreateMapping} className="p-8 space-y-6">
                {/* sensor MAC (read-only) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Sensor MAC Address</label>
                  <input
                    type="text"
                    value={mapForm.sensorMac}
                    readOnly
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 font-mono text-gray-700"
                  />
                </div>

                {/* Tuya device dropdown */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Tuya Device ID</label>
                  <select
                    value={mapForm.tuyaDeviceId}
                    onChange={(e) => setMapForm({ ...mapForm, tuyaDeviceId: e.target.value })}
                    required
                    disabled={tuyaLoading}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono bg-white disabled:bg-gray-100"
                  >
                    <option value="">{tuyaLoading ? 'Loading…' : 'Select a Tuya plug'}</option>
                    {tuyaDevices.map((d) => (
                      <option key={d.tuya_device_id} value={d.tuya_device_id}>
                        {(d.name || d.tuya_device_id) + (d.online === false ? ' (offline)' : '')}
                      </option>
                    ))}
                  </select>
                  <p className="mt-2 text-sm text-gray-600">Select a registered plug.</p>
                </div>

                {/* enable checkbox */}
                <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <input
                    type="checkbox"
                    id="enabledCb"
                    checked={mapForm.enabled}
                    onChange={(e) => setMapForm({ ...mapForm, enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                  <label htmlFor="enabledCb" className="text-sm font-medium text-gray-900">
                    Enable automation immediately (plug on when PM2.5 ≥ 9)
                  </label>
                </div>

                {/* buttons */}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowMapForm(false); setMapForm({ sensorMac: '', tuyaDeviceId: '', enabled: true }) }}
                    className="flex-1 py-3 px-6 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-all duration-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 py-3 px-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
                  >
                    {loading ? 'Creating…' : 'Create Mapping'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ════════════════ CSV DOWNLOAD MODAL ════════════════ */}
        {showCsvForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full">
              <div className="bg-gradient-to-br from-emerald-600 to-teal-600 px-8 py-6">
                <h2 className="text-2xl font-bold text-white mb-2">Download Sensor Data</h2>
                <p className="text-emerald-100">Export historical readings to CSV</p>
              </div>

              <form onSubmit={handleDownloadCSV} className="p-8 space-y-6">
                {/* sensor label (read-only) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Sensor</label>
                  <input
                    type="text"
                    value={`${csvForm.sensorName} (${csvForm.sensorMac})`}
                    readOnly
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                  />
                </div>

                {/* date range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
                    <input
                      type="date"
                      value={csvForm.startDate}
                      onChange={(e) => setCsvForm({ ...csvForm, startDate: e.target.value })}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
                    <input
                      type="date"
                      value={csvForm.endDate}
                      onChange={(e) => setCsvForm({ ...csvForm, endDate: e.target.value })}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* note */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-gray-700">
                    <strong>Note:</strong> CSV includes PM2.5, PM10, CO2, temperature, humidity, and battery for the selected range.
                  </p>
                </div>

                {/* buttons */}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowCsvForm(false); setCsvForm({ sensorMac: '', sensorName: '', startDate: '', endDate: '' }) }}
                    className="flex-1 py-3 px-6 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-all duration-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={csvDownloading}
                    className="flex-1 py-3 px-6 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-medium rounded-lg hover:from-emerald-700 hover:to-teal-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
                  >
                    {csvDownloading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Downloading…
                      </>
                    ) : (
                      <>
                        <Download className="w-5 h-5" />
                        Download CSV
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>

      {/* FOOTER */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <p>Air Quality Automation System v1.0</p>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <span>Backend Connected</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

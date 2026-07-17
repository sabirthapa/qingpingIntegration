import { useState } from 'react'
import {
  Link as LinkIcon,
  Power,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  formatTimestamp,
  getRelativeTime,
  getSensorConnectionStatus,
} from '../api/api.js'

export default function MappingCard({
  mapping,
  sensor,
  tuyaDevice,
  onToggle,
  onDelete,
}) {
  const [isDeleting, setIsDeleting] = useState(false)

  const sensorConnection =
    getSensorConnectionStatus(sensor || mapping)

  const plugOnline =
    typeof tuyaDevice?.online === 'boolean'
      ? tuyaDevice.online
      : null

  const plugState =
    tuyaDevice?.switch_state ??
    tuyaDevice?.switchState ??
    tuyaDevice?.state

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this mapping?')) return
    setIsDeleting(true)
    try {
      await onDelete(mapping.sensor_mac)
    } catch {
      setIsDeleting(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200 hover:shadow-xl transition-all duration-300">

      {/* colour bar */}
      <div className="bg-gradient-to-br from-purple-500 to-pink-500 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <LinkIcon className="w-6 h-6 text-white" />
            <div>
              <h3 className="text-white font-semibold">Sensor-Plug Mapping</h3>
              <p className="text-purple-100 text-sm font-mono">{mapping.sensor_mac}</p>
            </div>
          </div>

          {/* toggle */}
          <button
            onClick={() => onToggle(mapping)}
            className={`p-2 rounded-lg transition-all duration-200 ${
              mapping.enabled
                ? 'bg-green-400 hover:bg-green-500 text-green-900'
                : 'bg-gray-400 hover:bg-gray-500 text-gray-900'
            }`}
          >
            <Power className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* body */}
      <div className="p-6 space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-sm text-gray-600">Tuya Device</span>
            <span className="font-mono text-sm font-medium text-gray-900">{mapping.tuya_device_id}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Sensor status */}
            <div
              className={`p-3 rounded-lg border ${
                sensorConnection.known
                  ? sensorConnection.online
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                  : 'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-600">
                  Sensor
                </span>

                <span
                  className={`flex items-center gap-1 text-xs font-semibold ${
                    sensorConnection.known
                      ? sensorConnection.online
                        ? 'text-green-700'
                        : 'text-red-700'
                      : 'text-gray-600'
                  }`}
                >
                  {sensorConnection.online ? (
                    <Wifi className="w-4 h-4" />
                  ) : (
                    <WifiOff className="w-4 h-4" />
                  )}

                  {sensorConnection.known
                    ? sensorConnection.online
                      ? 'Online'
                      : 'Offline'
                    : 'Unknown'}
                </span>
              </div>

              <p className="mt-1 text-xs text-gray-500">
                {sensorConnection.lastSeenAt
                  ? `Last reading ${getRelativeTime(
                      sensorConnection.lastSeenAt
                    )}`
                  : 'No last-reading time'}
              </p>
            </div>

            {/* Smart plug status */}
            <div
              className={`p-3 rounded-lg border ${
                plugOnline === true
                  ? 'bg-green-50 border-green-200'
                  : plugOnline === false
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-600">
                  Smart plug
                </span>

                <span
                  className={`flex items-center gap-1 text-xs font-semibold ${
                    plugOnline === true
                      ? 'text-green-700'
                      : plugOnline === false
                        ? 'text-red-700'
                        : 'text-gray-600'
                  }`}
                >
                  {plugOnline === true ? (
                    <Wifi className="w-4 h-4" />
                  ) : (
                    <WifiOff className="w-4 h-4" />
                  )}

                  {plugOnline === true
                    ? 'Online'
                    : plugOnline === false
                      ? 'Offline'
                      : 'Unknown'}
                </span>
              </div>

              <p className="mt-1 text-xs text-gray-500">
                {plugState == null
                  ? tuyaDevice?.name || 'Status from Tuya'
                  : `Switch ${plugState ? 'ON' : 'OFF'}`}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-sm text-gray-600">Automation</span>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                mapping.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700'
              }`}
            >
              {mapping.enabled ? 'Automation Active' : 'Automation Paused'}
            </span>
          </div>

          {mapping.updated_at && (
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-sm text-gray-600">Last Updated</span>
              <span className="text-xs font-mono text-gray-900">{formatTimestamp(mapping.updated_at)}</span>
            </div>
          )}
        </div>

        {/* delete */}
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="w-full py-3 px-4 rounded-lg font-medium bg-red-500 text-white hover:bg-red-600 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 className="w-5 h-5" />
          {isDeleting ? 'Deleting…' : 'Delete Mapping'}
        </button>
      </div>
    </div>
  )
}

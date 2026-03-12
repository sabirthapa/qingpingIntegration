import { Activity, Link as LinkIcon, Power } from 'lucide-react'

function getPlugId(plug) {
  return plug.tuya_device_id || plug.device_id || plug.id || 'Unknown'
}

function getPlugName(plug) {
  return plug.name || plug.device_name || plug.product_name || 'Smart Plug'
}

function getPlugStatus(plug) {
  if (plug.online === false || plug.is_online === false) return 'Offline'
  return 'Online'
}

export default function SmartPlugCard({ plug, mappings }) {
  const plugId = getPlugId(plug)
  const plugName = getPlugName(plug)
  const status = getPlugStatus(plug)
  const mappedSensors = mappings.filter((mapping) => mapping.tuya_device_id === plugId)

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
      <div className="bg-gradient-to-br from-amber-500 to-orange-500 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <Power className="w-6 h-6 text-white flex-shrink-0" />
              <div className="min-w-0">
                <h3 className="text-white font-semibold text-lg truncate">{plugName}</h3>
                <p className="text-amber-100 text-sm font-mono truncate">{plugId}</p>
              </div>
            </div>
          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              status === 'Online'
                ? 'bg-emerald-300 text-emerald-950'
                : 'bg-slate-300 text-slate-900'
            }`}
          >
            {status}
          </span>
        </div>
      </div>

      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100">
            <p className="text-xs text-gray-600 mb-1">Linked Sensors</p>
            <p className="text-lg font-semibold text-gray-900">{mappedSensors.length}</p>
          </div>

          <div className="p-3 rounded-lg bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200">
            <p className="text-xs text-gray-600 mb-1">Category</p>
            <p className="text-sm font-medium text-gray-900 truncate">
              {plug.category || plug.product_name || 'Smart Plug'}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <LinkIcon className="w-4 h-4 text-amber-600" />
            <p className="text-sm font-medium text-gray-900">Mapped Sensors</p>
          </div>

          {mappedSensors.length === 0 ? (
            <p className="text-sm text-gray-600">No sensors are currently mapped to this plug.</p>
          ) : (
            <div className="space-y-2">
              {mappedSensors.map((mapping) => (
                <div
                  key={`${mapping.sensor_mac}-${mapping.tuya_device_id}`}
                  className="flex items-center justify-between rounded-lg bg-white px-3 py-2 border border-gray-200"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Activity className="w-4 h-4 text-cyan-600 flex-shrink-0" />
                    <span className="text-sm font-mono text-gray-900 truncate">{mapping.sensor_mac}</span>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      mapping.enabled
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {mapping.enabled ? 'Active' : 'Paused'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

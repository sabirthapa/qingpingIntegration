import { Activity, Wind, Link as LinkIcon, Download } from 'lucide-react'
import { formatTimestamp, getAirQualityStatus } from '../api/api.js'

export default function SensorCard({ device, onMapToPug, onDownloadCSV, hasMappingExisting }) {
  const aqStatus = device.latest_pm25 ? getAirQualityStatus(device.latest_pm25) : null

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">

      {/* colour bar */}
      <div className="bg-gradient-to-br from-blue-500 to-cyan-500 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-white" />
          <div>
            <h3 className="text-white font-semibold text-lg">
              {device.device_name || device.product?.en_name || 'Air Monitor'}
            </h3>
            <p className="text-blue-100 text-sm font-mono">{device.sensor_mac}</p>
          </div>
        </div>
        <div
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            device.enabled ? 'bg-green-400 text-green-900' : 'bg-gray-400 text-gray-900'
          }`}
        >
          {device.enabled ? 'Active' : 'Inactive'}
        </div>
      </div>

      {/* body */}
      <div className="p-6 space-y-4">

        {/* air-quality badge */}
        {aqStatus && (
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600 mb-1">Air Quality</p>
              <p className={`text-2xl font-bold ${aqStatus.textColor}`}>{aqStatus.label}</p>
            </div>
            <div className={`w-16 h-16 rounded-full ${aqStatus.color} flex items-center justify-center`}>
              <Wind className="w-8 h-8 text-white" />
            </div>
          </div>
        )}

        {/* meta row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg">
            <p className="text-xs text-gray-600 mb-1">Product</p>
            <p className="font-mono text-sm font-semibold text-gray-900">{device.product?.code || 'N/A'}</p>
          </div>
          <div className="text-center p-3 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg">
            <p className="text-xs text-gray-600 mb-1">Bound</p>
            <p className="font-mono text-xs text-gray-900">{formatTimestamp(device.bound_at)}</p>
          </div>
        </div>

        {/* action buttons */}
        <div className="space-y-2">
          <button
            onClick={() => onMapToPug(device)}
            disabled={hasMappingExisting}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              hasMappingExisting
                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-700 hover:to-cyan-700 shadow-md hover:shadow-lg'
            }`}
          >
            <LinkIcon className="w-5 h-5" />
            {hasMappingExisting ? 'Already Mapped' : 'Map to Plug'}
          </button>

          <button
            onClick={() => onDownloadCSV(device)}
            className="w-full py-3 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 bg-emerald-600 text-white hover:bg-emerald-700 shadow-md hover:shadow-lg"
          >
            <Download className="w-5 h-5" />
            Download CSV
          </button>
        </div>
      </div>
    </div>
  )
}

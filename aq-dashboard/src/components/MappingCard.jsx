import { useState } from 'react'
import { Link as LinkIcon, Power, Trash2 } from 'lucide-react'
import { formatTimestamp } from '../api/api.js'

export default function MappingCard({ mapping, onToggle, onDelete }) {
  const [isDeleting, setIsDeleting] = useState(false)

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

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-sm text-gray-600">Status</span>
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

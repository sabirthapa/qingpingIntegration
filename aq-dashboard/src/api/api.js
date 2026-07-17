import { API_BASE_URL } from './fetchInterceptor.js'

// ─── API methods ──────────────────────────────────────────────

export const api = {
  async listTuyaDevices() {
    const r = await fetch(`${API_BASE_URL}/tuya/devices`)
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
    return r.json()
  },

  async listDevices(userId) {
    const r = await fetch(`${API_BASE_URL}/qingping/devices?user_id=${userId}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
    return r.json()
  },

  async listMappings(userId) {
    const r = await fetch(
      `${API_BASE_URL}/mapping/sensor-plug?user_id=${encodeURIComponent(userId)}`
    )
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
    return r.json()
  },

  async createMapping(userId, sensorMac, tuyaDeviceId, enabled = true) {
    const r = await fetch(`${API_BASE_URL}/mapping/sensor-plug`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        user_id:        userId,
        sensor_mac:     sensorMac,
        tuya_device_id: tuyaDeviceId,
        enabled,
      }),
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
    return r.json()
  },

  async deleteMapping(sensorMac) {
    const r = await fetch(`${API_BASE_URL}/mapping/sensor-plug`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ sensor_mac: sensorMac, delete: true }),
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
    return r.json()
  },

  async toggleMapping(userId, sensorMac, tuyaDeviceId, enabled) {
    return this.createMapping(userId, sensorMac, tuyaDeviceId, enabled)
  },
}

// ─── Utility helpers ──────────────────────────────────────────

export function normalizeEpochSeconds(value) {
  if (value == null || value === '') return null

  const n = Number(value)
  if (!Number.isFinite(n)) return null

  return n > 1e12 ? Math.floor(n / 1000) : Math.floor(n)
}

export function getRelativeTime(ts) {
  const seconds = normalizeEpochSeconds(ts)
  if (!seconds) return 'Never'

  const diff = Math.max(
    0,
    Math.floor(Date.now() / 1000) - seconds
  )

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`

  const days = Math.floor(diff / 86400)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export function getSensorConnectionStatus(
  device,
  thresholdSeconds = 300
) {
  if (typeof device?.online === 'boolean') {
    return {
      online: device.online,
      known: true,
      lastSeenAt: normalizeEpochSeconds(device.last_seen_at),
    }
  }

  const lastSeenAt = normalizeEpochSeconds(
    device?.last_seen_at ??
    device?.last_observed_at ??
    device?.received_at ??
    device?.latest_timestamp
  )

  if (!lastSeenAt) {
    return {
      online: false,
      known: false,
      lastSeenAt: null,
    }
  }

  const ageSeconds =
    Math.floor(Date.now() / 1000) - lastSeenAt

  return {
    online: ageSeconds <= thresholdSeconds,
    known: true,
    lastSeenAt,
  }
}

export function formatTimestamp(ts) {
  return ts ? new Date(ts * 1000).toLocaleString() : 'N/A'
}

export function formatDateForAPI(date) {
  const d = new Date(date)
  return (
    `${d.getFullYear()}-` +
    `${String(d.getMonth() + 1).padStart(2, '0')}-` +
    `${String(d.getDate()).padStart(2, '0')}`
  )
}

export function getDefaultDateRange() {
  const end   = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 7)
  return { start: formatDateForAPI(start), end: formatDateForAPI(end) }
}

export function getAirQualityStatus(pm25) {
  if (pm25 == null) return { label: 'Unknown',   color: 'bg-gray-500',    textColor: 'text-gray-700'    }
  if (pm25 < 9)     return { label: 'Good',      color: 'bg-emerald-500', textColor: 'text-emerald-700' }
  if (pm25 < 35)    return { label: 'Moderate',  color: 'bg-yellow-500',  textColor: 'text-yellow-700'  }
  if (pm25 < 55)    return { label: 'Unhealthy', color: 'bg-orange-500',  textColor: 'text-orange-700'  }
  return { label: 'Hazardous', color: 'bg-red-500', textColor: 'text-red-700' }
}

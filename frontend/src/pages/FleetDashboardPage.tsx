import { FormEvent, useEffect, useMemo, useState } from 'react'

type DeviceRow = {
  id: string
  name: string
  status: string
  version: string | null
  last_seen: string | null
}

type StatusPreset = 'online' | 'offline' | 'stale' | 'error'

export function FleetDashboardPage() {
  const [status, setStatus] = useState('')
  const [version, setVersion] = useState('')
  const [devices, setDevices] = useState<DeviceRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const summary = useMemo(() => {
    const byStatus = devices.reduce<Record<string, number>>((acc, device) => {
      const key = device.status || 'unknown'
      acc[key] = (acc[key] ?? 0) + 1
      return acc
    }, {})
    return {
      total: devices.length,
      online: byStatus.online ?? 0,
      offline: byStatus.offline ?? 0,
      stale: byStatus.stale ?? 0,
      error: byStatus.error ?? 0,
    }
  }, [devices])

  async function loadDevices(event?: FormEvent, next?: { status?: string; version?: string }) {
    event?.preventDefault()
    setError(null)
    setLoading(true)

    const effectiveStatus = (next?.status ?? status).trim()
    const effectiveVersion = (next?.version ?? version).trim()

    const params = new URLSearchParams()
    if (effectiveStatus) params.set('status', effectiveStatus)
    if (effectiveVersion) params.set('version', effectiveVersion)

    try {
      const response = await fetch(`/api/v1/device/list?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const payload = (await response.json()) as DeviceRow[]
      setDevices(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load fleet')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDevices()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function exportCsv() {
    const params = new URLSearchParams()
    if (status.trim()) params.set('status', status.trim())
    if (version.trim()) params.set('version', version.trim())

    const response = await fetch(`/api/v1/device/export.csv?${params.toString()}`)
    if (!response.ok) {
      setError(`CSV export failed (HTTP ${response.status})`)
      return
    }
    const text = await response.text()
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'devices.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function applyStatusPreset(preset: StatusPreset) {
    setStatus(preset)
    void loadDevices(undefined, { status: preset, version })
  }

  function resetFilters() {
    setStatus('')
    setVersion('')
    void loadDevices(undefined, { status: '', version: '' })
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Device Fleet Dashboard</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Filter devices, inspect fleet status and export inventory CSV.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 8, marginBottom: 12 }}>
        <Stat label="Total" value={summary.total} />
        <Stat label="Online" value={summary.online} accent="#166534" />
        <Stat label="Offline" value={summary.offline} accent="#6b7280" />
        <Stat label="Stale" value={summary.stale} accent="#b45309" />
        <Stat label="Error" value={summary.error} accent="#b91c1c" />
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
        {(['online', 'offline', 'stale', 'error'] as StatusPreset[]).map((preset) => (
          <button key={preset} type="button" onClick={() => applyStatusPreset(preset)}>
            {preset}
          </button>
        ))}
        <button type="button" onClick={resetFilters}>
          Reset filters
        </button>
      </div>

      <form onSubmit={loadDevices} style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          placeholder="status (online/offline/stale/error)"
          style={{ padding: 8, minWidth: 220 }}
        />
        <input
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          placeholder="version"
          style={{ padding: 8, minWidth: 140 }}
        />
        <button type="submit" style={{ padding: '8px 10px' }}>
          {loading ? 'Refreshing…' : 'Refresh fleet'}
        </button>
        <button type="button" onClick={exportCsv} style={{ padding: '8px 10px' }}>
          Export CSV
        </button>
      </form>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Device</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Status</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Version</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Last seen</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((device) => (
            <tr key={device.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>
                <strong>{device.name}</strong>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{device.id}</div>
              </td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{device.status}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{device.version ?? '-'}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{device.last_seen ?? '-'}</td>
            </tr>
          ))}
          {devices.length === 0 && !loading && (
            <tr>
              <td colSpan={4} style={{ padding: 12, color: '#6b7280' }}>
                No devices loaded yet. Use filters and refresh.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

function Stat({ label, value, accent = '#111827' }: { label: string; value: number; accent?: string }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 10 }}>
      <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, color: accent }}>{value}</div>
    </div>
  )
}

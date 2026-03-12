import { useEffect, useState } from 'react'

type AlertRow = {
  id: number
  level: string
  source: string
  message: string
  status: string
  created_at: string
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertRow[]>([])
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function loadAlerts(nextStatus?: string) {
    const activeStatus = (nextStatus ?? status).trim()
    const params = new URLSearchParams()
    if (activeStatus) params.set('status', activeStatus)

    try {
      setError(null)
      const response = await fetch(`/api/v1/monitor/alerts?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const payload = (await response.json()) as AlertRow[]
      setAlerts(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts')
    }
  }

  useEffect(() => {
    void loadAlerts('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function updateAlert(alertId: number, action: 'ack' | 'resolve') {
    try {
      setError(null)
      const response = await fetch(`/api/v1/monitor/alerts/${alertId}/${action}`, {
        method: 'POST',
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
      }
      await loadAlerts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Alert action failed')
    }
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Alert Center</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Monitor alerts and execute acknowledge/resolve actions.
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          placeholder="status filter (open/acknowledged/resolved)"
          style={{ padding: 8, minWidth: 300 }}
        />
        <button
          type="button"
          style={{ padding: '8px 10px' }}
          onClick={() => {
            void loadAlerts()
          }}
        >
          Apply filter
        </button>
      </div>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>ID</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Level</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Source</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Message</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Status</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{alert.id}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{alert.level}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{alert.source}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{alert.message}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{alert.status}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8, display: 'flex', gap: 6 }}>
                <button type="button" onClick={() => void updateAlert(alert.id, 'ack')}>
                  Ack
                </button>
                <button type="button" onClick={() => void updateAlert(alert.id, 'resolve')}>
                  Resolve
                </button>
              </td>
            </tr>
          ))}
          {alerts.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: 12, color: '#6b7280' }}>
                No alerts yet for this filter.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

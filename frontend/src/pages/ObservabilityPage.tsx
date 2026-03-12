import { useEffect, useMemo, useState } from 'react'
import { StatCard } from '../components/StatCard'

type SummaryResponse = {
  devices: { total: number; online: number }
  alerts: { total: number; open: number; resolved: number }
  workers: {
    available: boolean
    workers: Record<string, { active: number; scheduled: number; reserved: number }>
  }
}

export function ObservabilityPage() {
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)

  const workerTotals = useMemo(() => {
    if (!data?.workers.available) {
      return { active: 0, scheduled: 0, reserved: 0, workers: 0 }
    }
    const values = Object.values(data.workers.workers)
    return {
      workers: values.length,
      active: values.reduce((sum, item) => sum + item.active, 0),
      scheduled: values.reduce((sum, item) => sum + item.scheduled, 0),
      reserved: values.reduce((sum, item) => sum + item.reserved, 0),
    }
  }, [data])

  async function loadSummary() {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/v1/observability/summary')
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`)
      }
      const body = (await response.json()) as SummaryResponse
      setData(body)
      setLastUpdatedAt(new Date().toISOString())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  function copySnapshot() {
    if (!data) return
    const snapshot = {
      captured_at: lastUpdatedAt,
      summary: data,
      worker_totals: workerTotals,
    }
    void navigator.clipboard.writeText(JSON.stringify(snapshot, null, 2))
  }

  useEffect(() => {
    void loadSummary()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = window.setInterval(() => {
      void loadSummary()
    }, 30000)
    return () => window.clearInterval(interval)
  }, [autoRefresh])

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>Observability</h2>
      <p style={{ marginTop: 0, color: '#4b5563' }}>Operational summary for devices, alerts and workers.</p>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button onClick={() => void loadSummary()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh summary'}
        </button>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(event) => setAutoRefresh(event.target.checked)}
          />
          Auto refresh (30s)
        </label>
        <button type="button" onClick={copySnapshot} disabled={!data}>
          Copy snapshot JSON
        </button>
      </div>

      {lastUpdatedAt && <p style={{ color: '#6b7280' }}>Last updated: {lastUpdatedAt}</p>}
      {error ? <p style={{ color: '#b91c1c' }}>Could not load summary: {error}</p> : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: 12,
          marginTop: 12,
        }}
      >
        <StatCard label="Devices total" value={data?.devices.total ?? '-'} />
        <StatCard label="Devices online" value={data?.devices.online ?? '-'} accent="#047857" />
        <StatCard label="Alerts open" value={data?.alerts.open ?? '-'} accent="#b45309" />
        <StatCard label="Alerts resolved" value={data?.alerts.resolved ?? '-'} accent="#0f766e" />
        <StatCard label="Workers" value={workerTotals.workers} accent="#1d4ed8" />
        <StatCard label="Active tasks" value={workerTotals.active} accent="#7c3aed" />
      </div>

      <h3 style={{ marginTop: 18 }}>Workers</h3>
      {!data?.workers.available ? (
        <p style={{ color: '#6b7280' }}>No worker telemetry available.</p>
      ) : (
        <>
          <p style={{ color: '#6b7280' }}>
            Totals — active: {workerTotals.active}, scheduled: {workerTotals.scheduled}, reserved:{' '}
            {workerTotals.reserved}
          </p>
          <table style={{ borderCollapse: 'collapse', width: '100%', maxWidth: 620 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 6 }}>Worker</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: 6 }}>Active</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: 6 }}>Scheduled</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: 6 }}>Reserved</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.workers.workers).map(([worker, stats]) => (
                <tr key={worker}>
                  <td style={{ padding: 6, borderBottom: '1px solid #f3f4f6' }}>{worker}</td>
                  <td style={{ textAlign: 'right', padding: 6, borderBottom: '1px solid #f3f4f6' }}>{stats.active}</td>
                  <td style={{ textAlign: 'right', padding: 6, borderBottom: '1px solid #f3f4f6' }}>{stats.scheduled}</td>
                  <td style={{ textAlign: 'right', padding: 6, borderBottom: '1px solid #f3f4f6' }}>{stats.reserved}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

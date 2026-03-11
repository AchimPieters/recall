import { useEffect, useState } from 'react'
import { StatCard } from '../components/StatCard'

type SummaryResponse = {
  devices: { total: number; online: number }
  alerts: { total: number; open: number; resolved: number }
  workers: {
    available: boolean
    workers: Record<
      string,
      { active: number; scheduled: number; reserved: number }
    >
  }
}

export function ObservabilityPage() {
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSummary()
  }, [])

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>Observability</h2>
      <p style={{ marginTop: 0, color: '#4b5563' }}>
        Operational summary for devices, alerts and workers.
      </p>
      <button onClick={() => void loadSummary()} disabled={loading}>
        {loading ? 'Refreshing...' : 'Refresh summary'}
      </button>
      {error ? (
        <p style={{ color: '#b91c1c' }}>Could not load summary: {error}</p>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: 12,
          marginTop: 12,
        }}
      >
        <StatCard label="Devices total" value={data?.devices.total ?? '-'} />
        <StatCard
          label="Devices online"
          value={data?.devices.online ?? '-'}
          accent="#047857"
        />
        <StatCard
          label="Alerts open"
          value={data?.alerts.open ?? '-'}
          accent="#b45309"
        />
        <StatCard
          label="Alerts resolved"
          value={data?.alerts.resolved ?? '-'}
          accent="#0f766e"
        />
      </div>

      <h3 style={{ marginTop: 18 }}>Workers</h3>
      {!data?.workers.available ? (
        <p style={{ color: '#6b7280' }}>No worker telemetry available.</p>
      ) : (
        <table
          style={{ borderCollapse: 'collapse', width: '100%', maxWidth: 620 }}
        >
          <thead>
            <tr>
              <th
                style={{
                  textAlign: 'left',
                  borderBottom: '1px solid #e5e7eb',
                  padding: 6,
                }}
              >
                Worker
              </th>
              <th
                style={{
                  textAlign: 'right',
                  borderBottom: '1px solid #e5e7eb',
                  padding: 6,
                }}
              >
                Active
              </th>
              <th
                style={{
                  textAlign: 'right',
                  borderBottom: '1px solid #e5e7eb',
                  padding: 6,
                }}
              >
                Scheduled
              </th>
              <th
                style={{
                  textAlign: 'right',
                  borderBottom: '1px solid #e5e7eb',
                  padding: 6,
                }}
              >
                Reserved
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.workers.workers).map(([worker, stats]) => (
              <tr key={worker}>
                <td style={{ padding: 6, borderBottom: '1px solid #f3f4f6' }}>
                  {worker}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    padding: 6,
                    borderBottom: '1px solid #f3f4f6',
                  }}
                >
                  {stats.active}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    padding: 6,
                    borderBottom: '1px solid #f3f4f6',
                  }}
                >
                  {stats.scheduled}
                </td>
                <td
                  style={{
                    textAlign: 'right',
                    padding: 6,
                    borderBottom: '1px solid #f3f4f6',
                  }}
                >
                  {stats.reserved}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

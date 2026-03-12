import { useEffect, useState } from 'react'
import { StatCard } from '../components/StatCard'

type AnalyticsSummary = {
  device_uptime_percent: number
  content_impressions: number
  playback_errors_24h: number
  screen_activity_24h: number
  total_devices: number
}

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch('/api/v1/analytics/summary')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = (await response.json()) as AnalyticsSummary
        setData(payload)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      }
    }
    void load()
  }, [])

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Analytics</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Device uptime, impressions, playback errors and screen activity.
      </p>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
          <StatCard label="Device uptime" value={`${data.device_uptime_percent}%`} />
          <StatCard label="Content impressions" value={data.content_impressions} />
          <StatCard label="Playback errors (24h)" value={data.playback_errors_24h} />
          <StatCard label="Screen activity (24h)" value={data.screen_activity_24h} />
        </div>
      )}
    </section>
  )
}

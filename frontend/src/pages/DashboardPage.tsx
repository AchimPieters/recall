import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { StatCard } from '../components/StatCard'

type ObservabilitySummary = {
  devices: { total: number; online: number }
  alerts: { total: number; open: number; resolved: number }
}

type AnalyticsSummary = {
  device_uptime_percent: number
  content_impressions: number
  playback_errors_24h: number
  screen_activity_24h: number
}

export function DashboardPage() {
  const [obs, setObs] = useState<ObservabilitySummary | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        setError(null)
        const [obsRes, analyticsRes] = await Promise.all([
          fetch('/api/v1/observability/summary'),
          fetch('/api/v1/analytics/summary'),
        ])

        if (!obsRes.ok) throw new Error(`Observability HTTP ${obsRes.status}`)
        if (!analyticsRes.ok) throw new Error(`Analytics HTTP ${analyticsRes.status}`)

        setObs((await obsRes.json()) as ObservabilitySummary)
        setAnalytics((await analyticsRes.json()) as AnalyticsSummary)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      }
    }
    void load()
  }, [])

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Enterprise Dashboard</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Unified snapshot of fleet, alerting and analytics health.
      </p>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
        <StatCard label="Devices total" value={obs?.devices.total ?? '-'} />
        <StatCard label="Devices online" value={obs?.devices.online ?? '-'} accent="#047857" />
        <StatCard label="Alerts open" value={obs?.alerts.open ?? '-'} accent="#b45309" />
        <StatCard label="Device uptime" value={analytics ? `${analytics.device_uptime_percent}%` : '-'} accent="#2563eb" />
        <StatCard label="Impressions" value={analytics?.content_impressions ?? '-'} />
        <StatCard label="Playback errors (24h)" value={analytics?.playback_errors_24h ?? '-'} accent="#b91c1c" />
      </div>

      <h3 style={{ marginTop: 20 }}>Quick actions</h3>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <Link to="/fleet">Open Fleet Dashboard</Link>
        <Link to="/ota-updates">Open OTA Manager</Link>
        <Link to="/alerts">Open Alert Center</Link>
        <Link to="/analytics">Open Analytics</Link>
      </div>
    </section>
  )
}

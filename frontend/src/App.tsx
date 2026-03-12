import { Link, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { DevicesPage } from './pages/DevicesPage'
import { MediaPage } from './pages/MediaPage'
import { PlaylistsPage } from './pages/PlaylistsPage'
import { SchedulesPage } from './pages/SchedulesPage'
import { AlertsPage } from './pages/AlertsPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { SettingsPage } from './pages/SettingsPage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { ObservabilityPage } from './pages/ObservabilityPage'
import { OtaUpdatesPage } from './pages/OtaUpdatesPage'
import { FleetDashboardPage } from './pages/FleetDashboardPage'

const links = [
  ['/', 'Dashboard'],
  ['/devices', 'Devices'],
  ['/media', 'Media'],
  ['/playlists', 'Playlists'],
  ['/schedules', 'Schedules'],
  ['/alerts', 'Alerts'],
  ['/settings', 'Settings'],
  ['/audit-logs', 'Audit logs'],
  ['/observability', 'Observability'],
  ['/analytics', 'Analytics'],
  ['/ota-updates', 'OTA manager'],
  ['/fleet', 'Fleet dashboard'],
]

export function App() {
  return (
    <div style={{ fontFamily: 'sans-serif', padding: 16 }}>
      <h1>Recall Platform v2</h1>
      <nav style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {links.map(([href, label]) => (
          <Link key={href} to={href}>
            {label}
          </Link>
        ))}
      </nav>
      <hr />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/devices" element={<DevicesPage />} />
        <Route path="/media" element={<MediaPage />} />
        <Route path="/playlists" element={<PlaylistsPage />} />
        <Route path="/schedules" element={<SchedulesPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/audit-logs" element={<AuditLogsPage />} />
        <Route path="/observability" element={<ObservabilityPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/ota-updates" element={<OtaUpdatesPage />} />
        <Route path="/fleet" element={<FleetDashboardPage />} />
      </Routes>
    </div>
  )
}

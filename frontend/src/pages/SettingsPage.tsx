import { FormEvent, useEffect, useState } from 'react'

type SettingsPayload = {
  site_name?: string
  timezone?: string
  language?: string
  heartbeat_interval?: number
  default_playlist_id?: number
  display_brightness?: number
  volume?: number
}

type HistoryRow = {
  version: number
  value: string
  changed_by: string
  reason: string
  changed_at: string
}

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsPayload>({})
  const [historyKey, setHistoryKey] = useState('site_name')
  const [history, setHistory] = useState<HistoryRow[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadSettings() {
    try {
      setError(null)
      const response = await fetch('/api/v1/settings?scope=organization')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = (await response.json()) as SettingsPayload
      setSettings(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    }
  }

  async function loadHistory(key: string) {
    try {
      setError(null)
      const response = await fetch(
        `/api/v1/settings/history/${encodeURIComponent(key)}?scope=organization&limit=10`,
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = (await response.json()) as HistoryRow[]
      setHistory(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    }
  }

  useEffect(() => {
    void loadSettings()
    void loadHistory(historyKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function saveSettings(event: FormEvent) {
    event.preventDefault()
    setMessage(null)
    setError(null)

    try {
      const response = await fetch('/api/v1/settings?scope=organization', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload?.detail ?? `HTTP ${response.status}`)
      setMessage('Settings updated successfully.')
      setSettings(payload as SettingsPayload)
      await loadHistory(historyKey)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    }
  }

  return (
    <section style={{ padding: 16, maxWidth: 900 }}>
      <h2 style={{ marginBottom: 4 }}>Settings Console</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Manage organization settings and inspect version history.
      </p>

      <form onSubmit={saveSettings} style={{ display: 'grid', gap: 10, marginBottom: 16 }}>
        <label style={{ display: 'grid', gap: 4 }}>
          Site name
          <input
            value={settings.site_name ?? ''}
            onChange={(e) => setSettings((prev) => ({ ...prev, site_name: e.target.value }))}
            style={{ padding: 8 }}
          />
        </label>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          <label style={{ display: 'grid', gap: 4 }}>
            Timezone
            <input
              value={settings.timezone ?? ''}
              onChange={(e) => setSettings((prev) => ({ ...prev, timezone: e.target.value }))}
              style={{ padding: 8 }}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            Language
            <input
              value={settings.language ?? ''}
              onChange={(e) => setSettings((prev) => ({ ...prev, language: e.target.value }))}
              style={{ padding: 8 }}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            Heartbeat interval
            <input
              type="number"
              value={settings.heartbeat_interval ?? 30}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, heartbeat_interval: Number(e.target.value) }))
              }
              style={{ padding: 8 }}
            />
          </label>
        </div>

        <button type="submit" style={{ width: 180, padding: '10px 12px' }}>
          Save settings
        </button>
      </form>

      {message && <p style={{ color: '#166534' }}>{message}</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <h3>Setting history</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input
          value={historyKey}
          onChange={(e) => setHistoryKey(e.target.value)}
          placeholder="setting key"
          style={{ padding: 8, minWidth: 220 }}
        />
        <button
          type="button"
          onClick={() => {
            void loadHistory(historyKey)
          }}
        >
          Refresh history
        </button>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Version</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Value</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Changed by</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Reason</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Changed at</th>
          </tr>
        </thead>
        <tbody>
          {history.map((row) => (
            <tr key={`${row.version}-${row.changed_at}`}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.version}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.value}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.changed_by}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.reason}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.changed_at}</td>
            </tr>
          ))}
          {history.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: 12, color: '#6b7280' }}>
                No history for this key yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

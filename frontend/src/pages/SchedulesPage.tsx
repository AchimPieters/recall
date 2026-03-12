import { FormEvent, useState } from 'react'

type PreviewResponse = {
  target: string
  at: string | null
  playlist_id: number | null
}

type ScheduleCreatePayload = {
  playlist_id: number
  target: string
  starts_at: string
  ends_at: string
  recurrence: string
  priority: number
  timezone: string
}

type ExceptionPayload = {
  schedule_id: number
  starts_at: string
  ends_at: string
  reason: string
}

type BlackoutPayload = {
  target: string
  starts_at: string
  ends_at: string
  reason: string
}

async function apiRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, init)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error((payload as { detail?: string })?.detail ?? `HTTP ${response.status}`)
  }
  return payload
}

export function SchedulesPage() {
  const [previewTarget, setPreviewTarget] = useState('all')
  const [previewAt, setPreviewAt] = useState('')
  const [previewResult, setPreviewResult] = useState<PreviewResponse | null>(null)

  const [scheduleForm, setScheduleForm] = useState<ScheduleCreatePayload>({
    playlist_id: 1,
    target: 'all',
    starts_at: '',
    ends_at: '',
    recurrence: 'once',
    priority: 100,
    timezone: 'UTC',
  })

  const [exceptionForm, setExceptionForm] = useState<ExceptionPayload>({
    schedule_id: 1,
    starts_at: '',
    ends_at: '',
    reason: 'Maintenance',
  })

  const [blackoutForm, setBlackoutForm] = useState<BlackoutPayload>({
    target: 'all',
    starts_at: '',
    ends_at: '',
    reason: 'Planned outage',
  })

  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function previewSchedule() {
    try {
      setError(null)
      const params = new URLSearchParams({ target: previewTarget.trim() || 'all' })
      if (previewAt.trim()) {
        params.set('at', new Date(previewAt).toISOString())
      }
      const payload = (await apiRequest(`/api/v1/playlists/resolve/preview?${params.toString()}`)) as PreviewResponse
      setPreviewResult(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview schedule resolution')
    }
  }

  async function createSchedule(event: FormEvent) {
    event.preventDefault()
    try {
      setMessage(null)
      setError(null)
      await apiRequest(`/api/v1/playlists/${scheduleForm.playlist_id}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: scheduleForm.target,
          starts_at: new Date(scheduleForm.starts_at).toISOString(),
          ends_at: new Date(scheduleForm.ends_at).toISOString(),
          recurrence: scheduleForm.recurrence,
          priority: scheduleForm.priority,
          timezone: scheduleForm.timezone,
        }),
      })
      setMessage('Schedule created successfully.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create schedule')
    }
  }

  async function createException(event: FormEvent) {
    event.preventDefault()
    try {
      setMessage(null)
      setError(null)
      await apiRequest(`/api/v1/playlists/schedules/${exceptionForm.schedule_id}/exceptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          starts_at: new Date(exceptionForm.starts_at).toISOString(),
          ends_at: new Date(exceptionForm.ends_at).toISOString(),
          reason: exceptionForm.reason,
        }),
      })
      setMessage('Schedule exception added successfully.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add exception')
    }
  }

  async function createBlackout(event: FormEvent) {
    event.preventDefault()
    try {
      setMessage(null)
      setError(null)
      await apiRequest('/api/v1/playlists/schedules/blackouts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: blackoutForm.target,
          starts_at: new Date(blackoutForm.starts_at).toISOString(),
          ends_at: new Date(blackoutForm.ends_at).toISOString(),
          reason: blackoutForm.reason,
        }),
      })
      setMessage('Blackout window created successfully.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create blackout window')
    }
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Scheduling Console</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Plan playlist windows, exceptions and blackout periods, and preview active resolution.
      </p>

      {message && <p style={{ color: '#166534' }}>{message}</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <div style={{ display: 'grid', gap: 16 }}>
        <section style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Resolution preview</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              value={previewTarget}
              onChange={(e) => setPreviewTarget(e.target.value)}
              placeholder="target (all/device/group)"
              style={{ padding: 8, minWidth: 220 }}
            />
            <input
              type="datetime-local"
              value={previewAt}
              onChange={(e) => setPreviewAt(e.target.value)}
              style={{ padding: 8 }}
            />
            <button type="button" onClick={() => void previewSchedule()}>
              Preview
            </button>
          </div>
          {previewResult && (
            <p style={{ marginBottom: 0 }}>
              Active playlist for <strong>{previewResult.target}</strong>: {previewResult.playlist_id ?? 'none'}
            </p>
          )}
        </section>

        <section style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Create schedule</h3>
          <form onSubmit={createSchedule} style={{ display: 'grid', gap: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Playlist ID
                <input
                  type="number"
                  min={1}
                  value={scheduleForm.playlist_id}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({ ...prev, playlist_id: Number(e.target.value) || 1 }))
                  }
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Target
                <input
                  value={scheduleForm.target}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, target: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Recurrence
                <input
                  value={scheduleForm.recurrence}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, recurrence: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Starts at
                <input
                  type="datetime-local"
                  value={scheduleForm.starts_at}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, starts_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Ends at
                <input
                  type="datetime-local"
                  value={scheduleForm.ends_at}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, ends_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Priority
                <input
                  type="number"
                  min={0}
                  value={scheduleForm.priority}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({ ...prev, priority: Number(e.target.value) || 0 }))
                  }
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <label>
              Timezone
              <input
                value={scheduleForm.timezone}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, timezone: e.target.value }))}
                style={{ width: 220, padding: 8 }}
              />
            </label>
            <button type="submit" style={{ width: 180 }}>
              Create schedule
            </button>
          </form>
        </section>

        <section style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Add schedule exception</h3>
          <form onSubmit={createException} style={{ display: 'grid', gap: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Schedule ID
                <input
                  type="number"
                  min={1}
                  value={exceptionForm.schedule_id}
                  onChange={(e) =>
                    setExceptionForm((prev) => ({ ...prev, schedule_id: Number(e.target.value) || 1 }))
                  }
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Reason
                <input
                  value={exceptionForm.reason}
                  onChange={(e) => setExceptionForm((prev) => ({ ...prev, reason: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Starts at
                <input
                  type="datetime-local"
                  value={exceptionForm.starts_at}
                  onChange={(e) => setExceptionForm((prev) => ({ ...prev, starts_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Ends at
                <input
                  type="datetime-local"
                  value={exceptionForm.ends_at}
                  onChange={(e) => setExceptionForm((prev) => ({ ...prev, ends_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <button type="submit" style={{ width: 220 }}>
              Add schedule exception
            </button>
          </form>
        </section>

        <section style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Create blackout window</h3>
          <form onSubmit={createBlackout} style={{ display: 'grid', gap: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Target
                <input
                  value={blackoutForm.target}
                  onChange={(e) => setBlackoutForm((prev) => ({ ...prev, target: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Reason
                <input
                  value={blackoutForm.reason}
                  onChange={(e) => setBlackoutForm((prev) => ({ ...prev, reason: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
              <label>
                Starts at
                <input
                  type="datetime-local"
                  value={blackoutForm.starts_at}
                  onChange={(e) => setBlackoutForm((prev) => ({ ...prev, starts_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
              <label>
                Ends at
                <input
                  type="datetime-local"
                  value={blackoutForm.ends_at}
                  onChange={(e) => setBlackoutForm((prev) => ({ ...prev, ends_at: e.target.value }))}
                  style={{ width: '100%', padding: 8 }}
                />
              </label>
            </div>
            <button type="submit" style={{ width: 220 }}>
              Create blackout window
            </button>
          </form>
        </section>
      </div>
    </section>
  )
}

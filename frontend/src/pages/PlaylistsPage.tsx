import { FormEvent, useEffect, useState } from 'react'

type PlaylistRow = {
  id: number
  name: string
}

type ResolvePreview = {
  target: string
  at: string | null
  playlist_id: number | null
}

type LayoutRow = {
  id: number
  name: string
  definition_json: string
}

type LayoutPreview = {
  layout: { id: number; name: string; definition_json: string } | null
  zones: Array<{ id: number; name: string; x: number; y: number; width: number; height: number }>
  assignments: Array<{ zone_id: number; playlist_id: number }>
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string }
  if (!response.ok) {
    throw new Error(payload?.detail ?? `HTTP ${response.status}`)
  }
  return payload
}

export function PlaylistsPage() {
  const [playlists, setPlaylists] = useState<PlaylistRow[]>([])
  const [newName, setNewName] = useState('')
  const [target, setTarget] = useState('all')
  const [preview, setPreview] = useState<ResolvePreview | null>(null)

  const [layouts, setLayouts] = useState<LayoutRow[]>([])
  const [layoutName, setLayoutName] = useState('Main layout')
  const [layoutDefinition, setLayoutDefinition] = useState('{"rows":1,"cols":1}')
  const [previewLayoutId, setPreviewLayoutId] = useState<number | null>(null)
  const [layoutPreview, setLayoutPreview] = useState<LayoutPreview | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function loadPlaylists() {
    const response = await fetch('/api/v1/playlists')
    const payload = await parseResponse<PlaylistRow[]>(response)
    setPlaylists(payload)
  }

  async function loadLayouts() {
    const response = await fetch('/api/v1/playlists/layouts')
    const payload = await parseResponse<LayoutRow[]>(response)
    setLayouts(payload)
    if (payload.length > 0 && previewLayoutId === null) {
      setPreviewLayoutId(payload[0].id)
    }
  }

  useEffect(() => {
    ;(async () => {
      try {
        setError(null)
        await loadPlaylists()
        await loadLayouts()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load playlists')
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function createPlaylist(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim()) {
      setError('Playlist name is verplicht')
      return
    }

    try {
      setError(null)
      setMessage(null)
      await parseResponse(
        await fetch('/api/v1/playlists', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName.trim() }),
        }),
      )
      setNewName('')
      setMessage('Playlist created.')
      await loadPlaylists()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create playlist')
    }
  }

  async function loadPreview() {
    try {
      setError(null)
      const response = await fetch(`/api/v1/playlists/resolve/preview?target=${encodeURIComponent(target)}`)
      const payload = await parseResponse<ResolvePreview>(response)
      setPreview(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview')
    }
  }

  async function createLayout(event: FormEvent) {
    event.preventDefault()
    try {
      setError(null)
      setMessage(null)
      const payload = await parseResponse<LayoutRow>(
        await fetch('/api/v1/playlists/layouts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: layoutName.trim(), definition_json: layoutDefinition.trim() }),
        }),
      )
      setMessage(`Layout ${payload.name} created.`)
      await loadLayouts()
      setPreviewLayoutId(payload.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create layout')
    }
  }

  async function previewLayout() {
    if (!previewLayoutId) {
      setError('Selecteer eerst een layout-id')
      return
    }
    try {
      setError(null)
      const payload = await parseResponse<LayoutPreview>(
        await fetch(`/api/v1/playlists/layouts/${previewLayoutId}/preview`),
      )
      setLayoutPreview(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview layout')
    }
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Playlist Console</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Manage playlists, resolution targets and layout previews.
      </p>

      {message && <p style={{ color: '#166534' }}>{message}</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <form onSubmit={createPlaylist} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New playlist name"
          style={{ padding: 8, minWidth: 260 }}
        />
        <button type="submit">Create</button>
      </form>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          placeholder="resolve target (all/device/group)"
          style={{ padding: 8, minWidth: 260 }}
        />
        <button type="button" onClick={() => void loadPreview()}>
          Preview resolution
        </button>
      </div>

      {preview && (
        <p style={{ color: '#1f2937' }}>
          Active playlist for <strong>{preview.target}</strong>: {preview.playlist_id ?? 'none'}
        </p>
      )}

      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Layout Console</h3>

        <form onSubmit={createLayout} style={{ display: 'grid', gap: 8, marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              value={layoutName}
              onChange={(e) => setLayoutName(e.target.value)}
              placeholder="Layout name"
              style={{ padding: 8, minWidth: 220 }}
            />
            <input
              value={layoutDefinition}
              onChange={(e) => setLayoutDefinition(e.target.value)}
              placeholder='{"rows":1,"cols":1}'
              style={{ padding: 8, minWidth: 320 }}
            />
            <button type="submit">Create layout</button>
          </div>
        </form>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
          <label>
            Layout preview ID{' '}
            <input
              type="number"
              min={1}
              value={previewLayoutId ?? ''}
              onChange={(e) => setPreviewLayoutId(Number(e.target.value) || null)}
              style={{ width: 120, padding: 6 }}
            />
          </label>
          <button type="button" onClick={() => void previewLayout()}>
            Preview layout
          </button>
        </div>

        {layouts.length > 0 && (
          <p style={{ color: '#6b7280' }}>
            Layouts: {layouts.map((layout) => `${layout.id}:${layout.name}`).join(' | ')}
          </p>
        )}

        {layoutPreview && layoutPreview.layout && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: 10 }}>
            <p style={{ marginTop: 0 }}>
              Preview for layout <strong>{layoutPreview.layout.name}</strong> (#{layoutPreview.layout.id})
            </p>
            <p>Zones: {layoutPreview.zones.length}</p>
            <ul>
              {layoutPreview.zones.map((zone) => {
                const assignment = layoutPreview.assignments.find((row) => row.zone_id === zone.id)
                return (
                  <li key={zone.id}>
                    {zone.name} [{zone.x},{zone.y} {zone.width}x{zone.height}] → playlist{' '}
                    {assignment?.playlist_id ?? 'none'}
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>ID</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Name</th>
          </tr>
        </thead>
        <tbody>
          {playlists.map((playlist) => (
            <tr key={playlist.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{playlist.id}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{playlist.name}</td>
            </tr>
          ))}
          {playlists.length === 0 && (
            <tr>
              <td colSpan={2} style={{ padding: 12, color: '#6b7280' }}>
                No playlists available.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

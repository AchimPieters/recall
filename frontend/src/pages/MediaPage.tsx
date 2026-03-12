import { FormEvent, useEffect, useState } from 'react'

type MediaRow = {
  id: number
  name: string
  mime_type: string
  version: number | null
  workflow_state: string
  uploaded_at: string
}

export function MediaPage() {
  const [items, setItems] = useState<MediaRow[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function loadMedia() {
    try {
      setError(null)
      const response = await fetch('/api/v1/media')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = (await response.json()) as MediaRow[]
      setItems(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load media')
    }
  }

  useEffect(() => {
    void loadMedia()
  }, [])

  async function uploadMedia(event: FormEvent) {
    event.preventDefault()
    if (!selectedFile) {
      setError('Selecteer eerst een bestand')
      return
    }
    setError(null)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('/api/v1/media/upload', {
        method: 'POST',
        body: formData,
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload?.detail ?? `HTTP ${response.status}`)
      setMessage('Media upload succesvol verwerkt.')
      setSelectedFile(null)
      await loadMedia()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  async function transitionWorkflow(mediaId: number, state: string) {
    try {
      setError(null)
      const response = await fetch(`/api/v1/media/${mediaId}/workflow/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload?.detail ?? `HTTP ${response.status}`)
      setMessage(`Workflow bijgewerkt naar ${state}.`)
      await loadMedia()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Workflow transition failed')
    }
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Media Console</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Upload media assets and manage workflow transitions.
      </p>

      <form onSubmit={uploadMedia} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <input
          type="file"
          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit">Upload</button>
      </form>

      {message && <p style={{ color: '#166534' }}>{message}</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Name</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>MIME</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Version</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Workflow</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{item.name}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{item.mime_type}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{item.version ?? '-'}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{item.workflow_state}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => void transitionWorkflow(item.id, 'review')}>To review</button>
                <button type="button" onClick={() => void transitionWorkflow(item.id, 'approved')}>Approve</button>
                <button type="button" onClick={() => void transitionWorkflow(item.id, 'published')}>Publish</button>
                <button type="button" onClick={() => void transitionWorkflow(item.id, 'archived')}>Archive</button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: 12, color: '#6b7280' }}>
                No media items loaded.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

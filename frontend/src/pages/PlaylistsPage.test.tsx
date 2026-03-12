import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { PlaylistsPage } from './PlaylistsPage'

describe('PlaylistsPage', () => {
  it('supports layout preview and playlist resolution preview', async () => {
    const fetchMock = vi
      .fn()
      // initial playlists
      .mockResolvedValueOnce({ ok: true, json: async () => [{ id: 1, name: 'Default' }] })
      // initial layouts
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: 9, name: 'Main layout', definition_json: '{"rows":1,"cols":1}' }],
      })
      // resolution preview
      .mockResolvedValueOnce({ ok: true, json: async () => ({ target: 'all', at: null, playlist_id: 1 }) })
      // layout preview
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          layout: { id: 9, name: 'Main layout', definition_json: '{}' },
          zones: [{ id: 4, name: 'left', x: 0, y: 0, width: 50, height: 100 }],
          assignments: [{ zone_id: 4, playlist_id: 1 }],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<PlaylistsPage />)

    expect(await screen.findByText('Default')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Preview resolution' }))
    expect(await screen.findByText((text) => text.includes('Active playlist for'))).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Preview layout' }))

    expect(await screen.findByText((text) => text.includes('Preview for layout'))).toBeInTheDocument()
    expect(screen.getByText((text) => text.includes('left [0,0 50x100]'))).toBeInTheDocument()

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
    expect(String(fetchMock.mock.calls[2][0])).toContain('/api/v1/playlists/resolve/preview?target=all')
    expect(String(fetchMock.mock.calls[3][0])).toContain('/api/v1/playlists/layouts/9/preview')
  })
})

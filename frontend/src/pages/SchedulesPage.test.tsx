import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { SchedulesPage } from './SchedulesPage'

describe('SchedulesPage', () => {
  it('previews and submits schedule operations', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ target: 'all', at: null, playlist_id: 7 }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 1 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 2 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 3 }) })

    vi.stubGlobal('fetch', fetchMock)

    render(<SchedulesPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByText((content) => content.includes('Active playlist for'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes(': 7'))).toBeInTheDocument()

    fireEvent.change(screen.getAllByLabelText('Starts at')[0], { target: { value: '2026-03-12T10:00' } })
    fireEvent.change(screen.getAllByLabelText('Ends at')[0], { target: { value: '2026-03-12T12:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create schedule' }))

    fireEvent.change(screen.getByLabelText('Schedule ID'), { target: { value: '12' } })
    fireEvent.change(screen.getAllByLabelText('Starts at')[1], { target: { value: '2026-03-12T10:30' } })
    fireEvent.change(screen.getAllByLabelText('Ends at')[1], { target: { value: '2026-03-12T11:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add schedule exception' }))

    fireEvent.change(screen.getAllByLabelText('Starts at')[2], { target: { value: '2026-03-12T11:00' } })
    fireEvent.change(screen.getAllByLabelText('Ends at')[2], { target: { value: '2026-03-12T13:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create blackout window' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(4)
    })

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/v1/playlists/resolve/preview?')
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/v1/playlists/1/schedule')
    expect(String(fetchMock.mock.calls[2][0])).toContain('/api/v1/playlists/schedules/12/exceptions')
    expect(String(fetchMock.mock.calls[3][0])).toContain('/api/v1/playlists/schedules/blackouts')
  })
})

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { FleetDashboardPage } from './FleetDashboardPage'

describe('FleetDashboardPage', () => {
  it('loads devices and applies status preset filters', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          { id: 'dev-1', name: 'Lobby', status: 'online', version: '2.4.0', last_seen: '2026-03-12T10:00:00Z' },
          { id: 'dev-2', name: 'Bar', status: 'offline', version: '2.4.0', last_seen: null },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          { id: 'dev-1', name: 'Lobby', status: 'online', version: '2.4.0', last_seen: '2026-03-12T10:00:00Z' },
        ],
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<FleetDashboardPage />)

    expect(await screen.findByText('Lobby')).toBeInTheDocument()
    expect(screen.getByText('Bar')).toBeInTheDocument()
    expect(screen.getByText('Total')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'online' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/v1/device/list?status=online')
    expect(screen.getByPlaceholderText('status (online/offline/stale/error)')).toHaveValue('online')
  })
})

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { OtaUpdatesPage } from './OtaUpdatesPage'

describe('OtaUpdatesPage', () => {
  it('supports rollout presets and dry-run toggle', async () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'run-1', getRandomValues: (v: Uint8Array) => v, subtle: {} } as unknown as Crypto)

    const fetchMock = vi
      .fn()
      // initial groups load
      .mockResolvedValueOnce({ ok: true, json: async () => [{ id: 12, name: 'Storefronts' }] })
      // submit rollout
      .mockResolvedValueOnce({ ok: true, json: async () => ({ selected_count: 4 }) })

    vi.stubGlobal('fetch', fetchMock)

    render(<OtaUpdatesPage />)

    expect(await screen.findByText('Storefronts')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '50%' }))
    expect(screen.getByLabelText('Rollout percentage')).toHaveValue(50)

    fireEvent.change(screen.getByLabelText('Target version'), { target: { value: '2.4.0' } })
    fireEvent.click(screen.getByLabelText('Dry-run mode (uitzetten = live rollout)'))

    fireEvent.click(screen.getByRole('button', { name: 'Start rollout' }))

    expect(await screen.findByText('Rollout aangemaakt voor 4 devices.')).toBeInTheDocument()
    expect((await screen.findAllByText('Storefronts')).length).toBeGreaterThan(0)
    expect(screen.getByText('2.4.0')).toBeInTheDocument()
    expect(screen.getByText('live')).toBeInTheDocument()

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))

    const submitBody = JSON.parse(String(fetchMock.mock.calls[1][1]?.body)) as {
      action: string
      target_version: string
      rollout_percentage: number
      dry_run: boolean
    }

    expect(submitBody.target_version).toBe('2.4.0')
    expect(submitBody.rollout_percentage).toBe(50)
    expect(submitBody.dry_run).toBe(false)
  })
})

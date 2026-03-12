import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { ObservabilityPage } from './ObservabilityPage'

describe('ObservabilityPage', () => {
  it('loads summary, shows worker totals, and copies snapshot JSON', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', {
      clipboard: { writeText },
    } as unknown as Navigator)

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        devices: { total: 10, online: 8 },
        alerts: { total: 5, open: 2, resolved: 3 },
        workers: {
          available: true,
          workers: {
            'celery@worker-a': { active: 2, scheduled: 1, reserved: 0 },
            'celery@worker-b': { active: 1, scheduled: 3, reserved: 1 },
          },
        },
      }),
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<ObservabilityPage />)

    expect(await screen.findByText('Totals — active: 3, scheduled: 4, reserved: 1')).toBeInTheDocument()
    expect(screen.getByText('celery@worker-a')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Copy snapshot JSON' }))

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1))
    expect(String(writeText.mock.calls[0][0])).toContain('worker_totals')
  })
})

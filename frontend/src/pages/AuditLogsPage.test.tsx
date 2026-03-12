import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { AuditLogsPage } from './AuditLogsPage'

describe('AuditLogsPage', () => {
  it('loads audit rows and applies filters', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            id: 11,
            actor_type: 'user',
            actor_id: 'alice',
            organization_id: 1,
            action: 'settings.update',
            resource_type: 'settings',
            resource_id: 'site_name',
            ip_address: '10.0.0.5',
            user_agent: 'test',
            created_at: '2026-03-11T10:00:00Z',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<AuditLogsPage />)

    expect(await screen.findByText('user:alice')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('action'), {
      target: { value: 'device.reboot' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    const lastCallUrl = String(fetchMock.mock.calls[1][0])
    expect(lastCallUrl).toContain('/api/v1/security/audit/logs?')
    expect(lastCallUrl).toContain('action=device.reboot')
    expect(await screen.findByText('No audit log rows for this query.')).toBeInTheDocument()
  })
})

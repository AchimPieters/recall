import { FormEvent, useEffect, useState } from 'react'

type DeviceGroup = {
  id: number
  name: string
}

type ProvisioningTokenResponse = {
  token: string
  expires_at: string
  organization_id: number | null
  id: number
}

export function DevicesPage() {
  const [groups, setGroups] = useState<DeviceGroup[]>([])
  const [selectedGroup, setSelectedGroup] = useState<number | null>(null)
  const [expiresInMinutes, setExpiresInMinutes] = useState(60)
  const [createdToken, setCreatedToken] = useState<ProvisioningTokenResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadGroups() {
      try {
        const response = await fetch('/api/v1/device/groups')
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = (await response.json()) as DeviceGroup[]
        setGroups(payload)
        if (payload.length > 0) {
          setSelectedGroup(payload[0].id)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load groups')
      }
    }
    void loadGroups()
  }, [])

  async function createProvisioningToken(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setCreatedToken(null)

    try {
      const response = await fetch('/api/v1/device/provisioning/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ expires_in_minutes: expiresInMinutes }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload?.detail ?? `HTTP ${response.status}`)
      }
      setCreatedToken(payload as ProvisioningTokenResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Provisioning token creation failed')
    }
  }

  return (
    <section style={{ padding: 16, maxWidth: 760 }}>
      <h2 style={{ marginBottom: 4 }}>Device Provisioning Center</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Create provisioning tokens and prepare rollout by device group.
      </p>

      <form onSubmit={createProvisioningToken} style={{ display: 'grid', gap: 10, marginBottom: 14 }}>
        <label style={{ display: 'grid', gap: 4 }}>
          Target group (operator context)
          <select
            value={selectedGroup ?? ''}
            onChange={(e) => setSelectedGroup(Number(e.target.value))}
            style={{ padding: 8 }}
          >
            {groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          Token expiry (minutes)
          <input
            type="number"
            min={1}
            max={1440}
            value={expiresInMinutes}
            onChange={(e) => setExpiresInMinutes(Number(e.target.value))}
            style={{ padding: 8 }}
          />
        </label>

        <button type="submit" style={{ width: 220, padding: '10px 12px' }}>
          Create provisioning token
        </button>
      </form>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      {createdToken && (
        <section style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#f9fafb' }}>
          <h3 style={{ marginTop: 0 }}>Provisioning token created</h3>
          <p style={{ margin: '4px 0' }}>
            <strong>Token:</strong> <code>{createdToken.token}</code>
          </p>
          <p style={{ margin: '4px 0' }}>
            <strong>Expires:</strong> {createdToken.expires_at}
          </p>
          <p style={{ margin: '4px 0', color: '#6b7280' }}>
            Share this token securely with the device enrollment flow (`/api/v1/device/provision/enroll`).
          </p>
        </section>
      )}
    </section>
  )
}

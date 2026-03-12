import { FormEvent, useEffect, useState } from 'react'

type AuditLogRow = {
  id: number
  actor_type: string
  actor_id: string
  organization_id: number | null
  action: string
  resource_type: string
  resource_id: string
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

type AuditFilters = {
  actor_id: string
  action: string
  resource_type: string
  ip_address: string
  limit: number
}

const DEFAULT_FILTERS: AuditFilters = {
  actor_id: '',
  action: '',
  resource_type: '',
  ip_address: '',
  limit: 50,
}

export function AuditLogsPage() {
  const [rows, setRows] = useState<AuditLogRow[]>([])
  const [filters, setFilters] = useState<AuditFilters>(DEFAULT_FILTERS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadAuditLogs(nextFilters?: AuditFilters) {
    const activeFilters = nextFilters ?? filters
    const params = new URLSearchParams()

    if (activeFilters.actor_id.trim()) params.set('actor_id', activeFilters.actor_id.trim())
    if (activeFilters.action.trim()) params.set('action', activeFilters.action.trim())
    if (activeFilters.resource_type.trim()) params.set('resource_type', activeFilters.resource_type.trim())
    if (activeFilters.ip_address.trim()) params.set('ip_address', activeFilters.ip_address.trim())
    params.set('limit', String(activeFilters.limit))

    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`/api/v1/security/audit/logs?${params.toString()}`)
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
      }
      const payload = (await response.json()) as AuditLogRow[]
      setRows(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAuditLogs(DEFAULT_FILTERS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function applyFilters(event: FormEvent) {
    event.preventDefault()
    void loadAuditLogs(filters)
  }

  return (
    <section style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 4 }}>Audit Log Console</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Search critical platform activity by actor, action, resource and IP.
      </p>

      <form onSubmit={applyFilters} style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8 }}>
          <input
            value={filters.actor_id}
            onChange={(e) => setFilters((prev) => ({ ...prev, actor_id: e.target.value }))}
            placeholder="actor_id"
            style={{ padding: 8 }}
          />
          <input
            value={filters.action}
            onChange={(e) => setFilters((prev) => ({ ...prev, action: e.target.value }))}
            placeholder="action"
            style={{ padding: 8 }}
          />
          <input
            value={filters.resource_type}
            onChange={(e) => setFilters((prev) => ({ ...prev, resource_type: e.target.value }))}
            placeholder="resource_type"
            style={{ padding: 8 }}
          />
          <input
            value={filters.ip_address}
            onChange={(e) => setFilters((prev) => ({ ...prev, ip_address: e.target.value }))}
            placeholder="ip_address"
            style={{ padding: 8 }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label>
            Limit{' '}
            <input
              type="number"
              min={1}
              max={500}
              value={filters.limit}
              onChange={(e) => setFilters((prev) => ({ ...prev, limit: Number(e.target.value) || 50 }))}
              style={{ width: 80, padding: 6 }}
            />
          </label>
          <button type="submit">Apply filters</button>
          <button
            type="button"
            onClick={() => {
              setFilters(DEFAULT_FILTERS)
              void loadAuditLogs(DEFAULT_FILTERS)
            }}
          >
            Reset
          </button>
        </div>
      </form>

      {loading && <p style={{ color: '#6b7280' }}>Loading…</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
        <thead>
          <tr>
            {['ID', 'Actor', 'Action', 'Resource', 'IP', 'Created at'].map((header) => (
              <th key={header} style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.id}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>
                {row.actor_type}:{row.actor_id}
              </td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.action}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>
                {row.resource_type}:{row.resource_id}
              </td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.ip_address ?? '-'}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{row.created_at}</td>
            </tr>
          ))}
          {rows.length === 0 && !loading && (
            <tr>
              <td colSpan={6} style={{ padding: 12, color: '#6b7280' }}>
                No audit log rows for this query.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

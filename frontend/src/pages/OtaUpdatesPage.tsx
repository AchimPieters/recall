import { FormEvent, useEffect, useState } from 'react'

type DeviceGroup = {
  id: number
  name: string
}

type ActionKind = 'update' | 'rollback'

type RolloutPreset = '5' | '25' | '50' | '100'

type OtaRunSummary = {
  id: string
  action: ActionKind
  group: string
  targetVersion: string
  rolloutPercentage: number
  dryRun: boolean
  selectedCount: number
  timestamp: string
}

export function OtaUpdatesPage() {
  const [groups, setGroups] = useState<DeviceGroup[]>([])
  const [groupId, setGroupId] = useState<number | null>(null)
  const [targetVersion, setTargetVersion] = useState('')
  const [rolloutPercentage, setRolloutPercentage] = useState(25)
  const [action, setAction] = useState<ActionKind>('update')
  const [dryRun, setDryRun] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [runs, setRuns] = useState<OtaRunSummary[]>([])

  const selectedGroup = groups.find((group) => group.id === groupId)

  useEffect(() => {
    async function loadGroups() {
      try {
        const response = await fetch('/api/v1/device/groups')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = (await response.json()) as DeviceGroup[]
        setGroups(payload)
        if (payload.length > 0) {
          setGroupId(payload[0].id)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load groups')
      }
    }
    void loadGroups()
  }, [])

  function applyPreset(value: RolloutPreset) {
    setRolloutPercentage(Number(value))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!groupId) {
      setError('Selecteer eerst een device group')
      return
    }
    if (!targetVersion.trim()) {
      setError('Target version is verplicht')
      return
    }
    if (rolloutPercentage < 1 || rolloutPercentage > 100) {
      setError('Rollout percentage moet tussen 1 en 100 liggen')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`/api/v1/device/groups/${groupId}/bulk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action,
          target_version: targetVersion.trim(),
          rollout_percentage: rolloutPercentage,
          dry_run: dryRun,
        }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload?.detail ?? `HTTP ${response.status}`)
      }
      const selectedCount = Number(payload.selected_count ?? 0)
      const mode = dryRun ? 'Dry-run' : 'Rollout'
      setResult(`${mode} aangemaakt voor ${selectedCount} devices.`)
      setRuns((previous) => [
        {
          id: crypto.randomUUID(),
          action,
          group: selectedGroup?.name ?? String(groupId),
          targetVersion: targetVersion.trim(),
          rolloutPercentage,
          dryRun,
          selectedCount,
          timestamp: new Date().toISOString(),
        },
        ...previous,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OTA actie mislukt')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={{ padding: 16, maxWidth: 900 }}>
      <h2 style={{ marginBottom: 4 }}>OTA Update Manager</h2>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Plan staged updates/rollbacks per device group met dry-run of live rollout mode.
      </p>

      <form onSubmit={submit} style={{ display: 'grid', gap: 12 }}>
        <label style={{ display: 'grid', gap: 4 }}>
          Device group
          <select
            value={groupId ?? ''}
            onChange={(e) => setGroupId(Number(e.target.value))}
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
          Actie
          <select
            value={action}
            onChange={(e) => setAction(e.target.value as ActionKind)}
            style={{ padding: 8 }}
          >
            <option value="update">Update</option>
            <option value="rollback">Rollback</option>
          </select>
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          Target version
          <input
            value={targetVersion}
            onChange={(e) => setTargetVersion(e.target.value)}
            placeholder="bijv. 2.3.1"
            style={{ padding: 8 }}
          />
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          Rollout percentage
          <input
            type="number"
            min={1}
            max={100}
            value={rolloutPercentage}
            onChange={(e) => setRolloutPercentage(Number(e.target.value))}
            style={{ padding: 8 }}
          />
        </label>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {(['5', '25', '50', '100'] as RolloutPreset[]).map((preset) => (
            <button key={preset} type="button" onClick={() => applyPreset(preset)}>
              {preset}%
            </button>
          ))}
        </div>

        <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          Dry-run mode (uitzetten = live rollout)
        </label>

        <button type="submit" style={{ width: 200, padding: '10px 12px' }} disabled={loading}>
          {loading ? 'Submitting…' : dryRun ? 'Start dry-run' : 'Start rollout'}
        </button>
      </form>

      {result && <p style={{ color: '#166534', marginTop: 12 }}>{result}</p>}
      {error && <p style={{ color: '#b91c1c', marginTop: 12 }}>{error}</p>}

      <h3 style={{ marginTop: 20, marginBottom: 8 }}>Recent OTA runs (session)</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Timestamp</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Group</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Action</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Version</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Rollout</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Mode</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: 8 }}>Selected</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.timestamp}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.group}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.action}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.targetVersion}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.rolloutPercentage}%</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.dryRun ? 'dry-run' : 'live'}</td>
              <td style={{ borderBottom: '1px solid #f3f4f6', padding: 8 }}>{run.selectedCount}</td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={7} style={{ padding: 12, color: '#6b7280' }}>
                No OTA runs yet in this session.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  )
}

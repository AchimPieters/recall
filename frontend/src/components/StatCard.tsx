import type { ReactNode } from 'react'

type StatCardProps = {
  label: string
  value: string | number
  hint?: string
  accent?: string
  children?: ReactNode
}

export function StatCard({
  label,
  value,
  hint,
  accent = '#2563eb',
  children,
}: StatCardProps) {
  return (
    <section
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        padding: 14,
        minWidth: 180,
        background: '#fff',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}
    >
      <p style={{ margin: 0, fontSize: 12, color: '#6b7280' }}>{label}</p>
      <p
        style={{
          margin: '6px 0 0',
          fontSize: 28,
          fontWeight: 700,
          color: accent,
        }}
      >
        {value}
      </p>
      {hint ? (
        <p style={{ margin: '6px 0 0', fontSize: 12, color: '#4b5563' }}>
          {hint}
        </p>
      ) : null}
      {children}
    </section>
  )
}

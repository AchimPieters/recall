import { render, screen } from '@testing-library/react'
import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('renders label, value and hint', () => {
    render(<StatCard label="Devices" value={42} hint="All sites" />)

    expect(screen.getByText('Devices')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('All sites')).toBeInTheDocument()
  })
})

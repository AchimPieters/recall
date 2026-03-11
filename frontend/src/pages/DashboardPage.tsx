import { Link } from 'react-router-dom'

export function DashboardPage() {
  return (
    <section>
      <p>Dashboard is connected to the Recall API.</p>
      <p>
        Use the new <Link to="/observability">Observability</Link> screen for
        operational counters and worker status.
      </p>
    </section>
  )
}

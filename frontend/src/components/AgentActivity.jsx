import EmptyState from './EmptyState'
import Checkout from './Checkout'
import { IconActivity } from './icons'

export default function AgentActivity({ data, loading, error }) {
  const runs = data?.runs || []
  if (loading) return <div className="skeleton" style={{ height: 160 }} />
  if (error) return <div className="error-box">{error.message || 'Unable to load agent activity.'}</div>
  if (!runs.length) {
    return (
      <EmptyState
        icon={IconActivity}
        title="No agent runs yet"
        description="The Growth Agent will appear here after it analyzes available Test Mode transaction data."
      />
    )
  }
  return (
    <div className="runs">
      {runs.map((run) => (
        <article key={run.agent_run_id}>
          <small>{new Date(run.started_at).toLocaleString()}</small>
          <span className={'pill ' + (run.status === 'recommended' ? 'ok' : 'neutral')}>{run.status.replace('_', ' ')}</span>
          {run.priority && <span className={'pill ' + (run.priority === 'HIGH' ? 'ok' : run.priority === 'MEDIUM' ? 'warn' : 'neutral')} style={{ marginLeft: 8 }}>{run.priority}</span>}
          <p style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: 13 }}>{run.recommendation || run.reasoning}</p>
          <code>{run.agent_run_id}</code>
          <Checkout id={run.agent_run_id} />
        </article>
      ))}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { getExperimentHistory } from '../services/api'
import EmptyState from './EmptyState'
import MetricCard from './MetricCard'
import { IconActivity, IconAlert, IconBolt, IconCheck, IconPayments, IconPipeline } from './icons'

function decisionTone(status) {
  if (status === 'approved') return 'ok'
  if (status === 'rejected' || status === 'blocked') return 'bad'
  if (status === 'pending_approval') return 'warn'
  return 'neutral'
}
function executionTone(status) {
  if (status === 'payment_verified') return 'ok'
  if (status === 'order_created') return 'warn'
  if (status === 'failed') return 'bad'
  return 'neutral'
}
function outcomeTone(event) {
  if (event === 'payment_verified') return 'ok'
  if (event === 'payment_failed') return 'bad'
  if (event === 'payment_cancelled') return 'warn'
  if (event === 'test_order_created') return 'info'
  return 'neutral'
}
function pct(rate) {
  return rate == null ? undefined : `${Math.round(rate * 100)}%`
}

export default function ExperimentHistory() {
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    let cancelled = false
    getExperimentHistory()
      .then((data) => { if (!cancelled) setState({ loading: false, data }) })
      .catch((error) => { if (!cancelled) setState({ loading: false, error }) })
    return () => { cancelled = true }
  }, [])

  if (state.loading) return <div className="skeleton" style={{ height: 220 }} />
  if (state.error) return <div className="error-box">{state.error.message || 'Unable to load experiment history.'}</div>

  const { summary, history, learning } = state.data
  if (!summary.total_recommendations) {
    return (
      <EmptyState
        icon={IconActivity}
        title="Your experiment history will appear here"
        description="Run a Growth Demo or execute an approved recommendation to start building measurable history."
      />
    )
  }

  const summaryCards = [
    { icon: IconPipeline, label: 'Total Recommendations', value: summary.total_recommendations },
    { icon: IconCheck, label: 'Approved', value: summary.approved, foot: pct(summary.approval_rate) ? `${pct(summary.approval_rate)} approval rate` : undefined },
    { icon: IconAlert, label: 'Rejected', value: summary.rejected },
    { icon: IconBolt, label: 'Executed', value: summary.executed, foot: pct(summary.execution_rate) ? `${pct(summary.execution_rate)} of approved` : undefined },
    { icon: IconPayments, label: 'Payment Verified', value: summary.payment_verified, foot: pct(summary.payment_verification_rate) ? `${pct(summary.payment_verification_rate)} payment verification rate` : undefined },
  ]
  if (summary.failed > 0) summaryCards.push({ icon: IconAlert, label: 'Failed', value: summary.failed })

  return (
    <div>
      <div className="metric-grid quiet" style={{ marginBottom: 20 }}>
        {summaryCards.map((c) => <MetricCard key={c.label} icon={c.icon} label={c.label} value={c.value} foot={c.foot} />)}
      </div>

      <div className="card card-pad" style={{ marginBottom: 20 }}>
        <div className="section-head" style={{ marginBottom: 10 }}>
          <h2>AI Learning</h2>
          <span className="section-sub">Observed history only — not a prediction</span>
        </div>
        {learning.length ? (
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 8 }}>
            {learning.map((line, i) => (
              <li key={i} className="reasoning-evidence">{line}</li>
            ))}
          </ul>
        ) : (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No merchant decisions recorded yet.</p>
        )}
      </div>

      <div className="runs">
        {history.map((record) => (
          <article key={record.agent_run_id}>
            <small>{record.started_at ? new Date(record.started_at).toLocaleString() : ''}</small>
            <div className="pipeline-title-row" style={{ marginBottom: 6 }}>
              <b style={{ textTransform: 'capitalize' }}>{record.opportunity_type?.replace('_', ' ') || 'Opportunity'}</b>
              <span style={{ color: 'var(--text-faint)' }}>{record.recommended_product || '--'}</span>
            </div>
            <div className="pipeline-tags" style={{ marginBottom: 10 }}>
              <span className={'pill ' + decisionTone(record.decision_status)}>{record.decision_label}</span>
              <span className={'pill ' + executionTone(record.execution_status)}>{record.execution_label}</span>
              <span className={'pill ' + outcomeTone(record.outcome_event)}>{record.outcome_label}</span>
            </div>
            {record.expected_outcome && (
              <p className="reasoning-evidence" style={{ marginBottom: 4 }}><b>Expected:</b> {record.expected_outcome}</p>
            )}
            <p className="reasoning-evidence"><b>Observed:</b> {record.outcome_label}</p>
            <code>{record.agent_run_id}</code>
          </article>
        ))}
      </div>
    </div>
  )
}

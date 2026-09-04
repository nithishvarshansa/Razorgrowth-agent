import EmptyState from './EmptyState'
import { IconPipeline } from './icons'

// Confidence -> priority label mirrors the backend's own deterministic mapping
// (opportunity_ranking.PRIORITY_LABEL). Used only as a display fallback for the
// raw, unranked /api/analytics/opportunities list; real ranked results already
// carry this field from the server.
const PRIORITY_FROM_CONFIDENCE = { high: 'HIGH', medium: 'MEDIUM', low: 'LOW' }
const EVIDENCE_FROM_CONFIDENCE = { high: 'Strong', medium: 'Moderate', low: 'Limited' }

function keyOf(o) {
  return `${o.customer_id}|${o.recommended_product}|${o.opportunity_type}`
}

export default function OpportunityPipeline({ opportunities, selectedKey, emptyReason, onRunDemo, demoBusy }) {
  const items = opportunities || []
  if (!items.length) {
    return (
      <EmptyState
        icon={IconPipeline}
        title="No growth opportunities yet"
        description={emptyReason || 'The agent needs at least two successful, product-identified Test Mode purchases before it can find an evidence-based opportunity.'}
        actionLabel={onRunDemo ? 'Run Growth Demo' : undefined}
        onAction={onRunDemo}
        actionBusy={demoBusy}
      />
    )
  }
  return (
    <div className="pipeline">
      {items.map((o, i) => {
        const priority = o.priority || PRIORITY_FROM_CONFIDENCE[o.confidence] || 'LOW'
        const evidenceStrength = o.evidence_strength || EVIDENCE_FROM_CONFIDENCE[o.confidence] || 'Limited'
        const selected = selectedKey && keyOf(o) === selectedKey
        return (
          <div className={'pipeline-item' + (selected ? ' selected' : '')} key={i}>
            <div className="pipeline-rank">{String(i + 1).padStart(2, '0')}</div>
            <div className="pipeline-body">
              <div className="pipeline-title-row">
                {selected && <span className="pill ok">AI selected</span>}
                <b>{o.opportunity_type.replace('_', ' ')}</b>
                <span style={{ color: 'var(--text-faint)' }}>{o.recommended_product}</span>
              </div>
              <div className="pipeline-meta">
                <span>Confidence: {o.confidence || '--'}</span>
                <span>Evidence: {evidenceStrength}</span>
              </div>
              <div className="pipeline-tags">
                <span className={'pill ' + (priority === 'HIGH' ? 'ok' : priority === 'MEDIUM' ? 'warn' : 'neutral')}>{priority}</span>
                {'eligible' in o && (o.already_decided
                  ? <span className="pill neutral">already decided</span>
                  : o.eligible
                    ? <span className="pill success">guardrail eligible</span>
                    : <span className="pill bad">guardrail blocked</span>)}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

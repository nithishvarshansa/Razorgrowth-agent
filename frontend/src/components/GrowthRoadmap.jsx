import { IconCheck, IconClock, IconTarget } from './icons'

function pillTone(state) {
  if (state === 'done') return 'ok'
  if (state === 'active' || state === 'pending') return 'warn'
  if (state === 'failed' || state === 'blocked') return 'bad'
  if (state === 'skipped') return 'neutral'
  return 'neutral'
}

function Marker({ state }) {
  if (state === 'done') return <span className="dc-marker"><IconCheck width={14} height={14} /></span>
  if (state === 'failed' || state === 'blocked') return <span className="dc-marker">✗</span>
  if (state === 'pending') return <span className="dc-marker"><IconClock width={13} height={13} /></span>
  if (state === 'skipped') return <span className="dc-marker">—</span>
  return <span className="dc-marker" />
}

function stageClass(state) {
  if (state === 'done') return 'dc-stage done'
  if (state === 'failed') return 'dc-stage failed'
  if (state === 'blocked') return 'dc-stage blocked'
  if (state === 'pending') return 'dc-stage pending'
  if (state === 'skipped') return 'dc-stage skipped'
  return 'dc-stage'
}

// Every field read below already exists on the real recommendation / guardrail /
// commerce / measurement objects produced elsewhere in the app (GrowthStrategy.jsx
// computes the same booleans from the same fields). This component only re-reads
// and labels that state — it never creates, approves, executes, or schedules anything.
function buildStages({ recommendation, guardrail, approved, rejected, blocked, pendingApproval, commerce, paymentVerified, executionFailed, failureReason, nextAction, nextEligible }) {
  const oppLabel = recommendation?.opportunity_type ? recommendation.opportunity_type.replace(/_/g, ' ') : 'Opportunity'

  const current = {
    key: 'current',
    title: 'Current action',
    state: recommendation ? 'done' : '',
    heading: recommendation ? oppLabel : 'No recommendation yet',
    lines: recommendation ? [
      recommendation.recommended_product ? `Recommended product: ${recommendation.recommended_product}` : null,
      recommendation.confidence ? `Confidence: ${recommendation.confidence}` : null,
      recommendation.expected_outcome ? `Expected outcome: ${recommendation.expected_outcome}` : null,
    ].filter(Boolean) : ['Run the Growth Demo to generate a recommendation.'],
    pillLabel: recommendation ? (recommendation.status ? recommendation.status.replace(/_/g, ' ') : 'Recommended') : 'None yet',
  }

  let decisionState = ''
  let decisionLabel = ''
  if (!recommendation) { decisionState = ''; decisionLabel = '' }
  else if (blocked) { decisionState = 'blocked'; decisionLabel = 'Blocked by guardrail' }
  else if (approved) { decisionState = 'done'; decisionLabel = 'Merchant approved' }
  else if (rejected) { decisionState = 'skipped'; decisionLabel = 'Merchant rejected' }
  else if (pendingApproval) { decisionState = 'pending'; decisionLabel = 'Awaiting merchant decision' }
  const decision = {
    key: 'decision',
    title: 'Merchant decision',
    state: decisionState,
    heading: decisionLabel || (recommendation ? 'Awaiting guardrail evaluation' : '--'),
    lines: guardrail?.reasons?.length ? guardrail.reasons : [],
    pillLabel: decisionLabel || undefined,
  }

  let execState = ''
  let execLabel = ''
  if (!recommendation) { execState = ''; execLabel = '' }
  else if (rejected) { execState = 'skipped'; execLabel = 'Not executed — rejected by merchant' }
  else if (blocked) { execState = 'skipped'; execLabel = 'Not executed — blocked by guardrail' }
  else if (executionFailed) { execState = 'failed'; execLabel = 'Execution failed' }
  else if (commerce) { execState = 'done'; execLabel = 'Test Mode order created' }
  else if (approved) { execState = 'pending'; execLabel = 'Ready for Test Mode execution' }
  else if (pendingApproval) { execState = 'pending'; execLabel = 'Waiting for approval' }
  const execution = {
    key: 'execution',
    title: 'Execution',
    state: execState,
    heading: execLabel || '--',
    lines: [
      executionFailed && failureReason ? `Reason: ${failureReason}` : null,
      commerce?.razorpay_order_id ? `Test Mode order: ${commerce.razorpay_order_id}` : null,
    ].filter(Boolean),
    pillLabel: execLabel || undefined,
  }

  let measureState = ''
  let measureLabel = ''
  if (!recommendation) { measureState = ''; measureLabel = '' }
  else if (rejected || blocked) { measureState = 'skipped'; measureLabel = 'Not applicable' }
  else if (executionFailed) { measureState = 'failed'; measureLabel = 'Execution/payment failure recorded' }
  else if (paymentVerified) { measureState = 'done'; measureLabel = 'Payment verified' }
  else if (approved) { measureState = 'pending'; measureLabel = 'Awaiting outcome' }
  const measurement = {
    key: 'measurement',
    title: 'Measurement',
    state: measureState,
    heading: measureLabel || '--',
    lines: [],
    pillLabel: measureLabel || undefined,
  }

  let nextState = ''
  let nextHeading = 'No new eligible action yet'
  let nextLines = []
  if (nextEligible) {
    nextState = 'done'
    nextHeading = `${(nextAction.opportunity_type || '').replace(/_/g, ' ')}${nextAction.recommended_product ? ' — ' + nextAction.recommended_product : ''}`
    nextLines = [nextAction.reasoning || nextAction.evidence?.[0]].filter(Boolean)
  } else if (nextAction) {
    nextState = ''
    nextHeading = 'No new eligible action yet'
    nextLines = [nextAction.reasoning].filter(Boolean)
  } else {
    nextState = ''
    nextHeading = 'No new eligible action yet'
    nextLines = ['After the current outcome is measured, the agent can evaluate the next eligible action.']
  }
  const next = {
    key: 'next',
    title: 'Next eligible action',
    state: nextState,
    heading: nextHeading,
    lines: nextLines,
    pillLabel: nextEligible ? 'Available' : undefined,
  }

  return [current, decision, execution, measurement, next]
}

export default function GrowthRoadmap(props) {
  const stages = buildStages(props)

  return (
    <div className="card card-pad" style={{ marginTop: 20 }}>
      <div className="section-head" style={{ marginBottom: 6 }}>
        <h2><IconTarget width={12} height={12} style={{ marginRight: 6, verticalAlign: -1 }} />Smart Growth Roadmap</h2>
        <span className="section-sub">Growth actions progress based on merchant decisions and measured outcomes.</span>
      </div>
      <p style={{ fontSize: 12.5, color: 'var(--text-faint)', margin: '4px 0 14px' }}>
        Current experiment → measure outcome → evaluate next eligible action.
      </p>
      <div className="roadmap-stages" role="list" aria-label="Smart Growth Roadmap">
        {stages.map((s) => (
          <div className={stageClass(s.state)} key={s.key} role="listitem">
            <Marker state={s.state} />
            <div className="dc-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <b>{s.title}</b>
                {s.pillLabel && <span className={'pill ' + pillTone(s.state)}>{s.pillLabel}</span>}
              </div>
              <small style={{ display: 'block', marginTop: 2, textTransform: 'none' }}>{s.heading}</small>
              {s.lines.map((line, i) => (
                <p className="reasoning-evidence" key={i} style={{ marginTop: 6 }}>{line}</p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

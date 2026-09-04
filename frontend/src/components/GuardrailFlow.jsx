import { IconCheck } from './icons'

function stepClass(state) {
  if (state === 'done') return 'gr-step done'
  if (state === 'active') return 'gr-step active'
  if (state === 'blocked') return 'gr-step blocked'
  return 'gr-step'
}

function Dot({ state }) {
  if (state === 'done') return <span className="gr-dot"><IconCheck width={15} height={15} /></span>
  if (state === 'blocked') return <span className="gr-dot">✗</span>
  return <span className="gr-dot" />
}

export default function GuardrailFlow({ hasRecommendation, guardrailEvaluated, guardrailPassed, approvalStatus, executed, measured }) {
  const recState = hasRecommendation ? 'done' : ''
  const guardrailState = !guardrailEvaluated ? (hasRecommendation ? 'active' : '') : guardrailPassed ? 'done' : 'blocked'
  const approvalState = approvalStatus === 'approved' ? 'done' : approvalStatus === 'rejected' ? 'blocked' : approvalStatus === 'pending' ? 'active' : ''
  const execState = executed ? 'done' : approvalStatus === 'approved' ? 'active' : ''
  const measureState = measured ? 'done' : executed ? 'active' : ''

  const steps = [
    { key: 'rec', label: 'AI Recommendation', hint: 'Evidence-based only', state: recState },
    { key: 'guardrail', label: guardrailState === 'blocked' ? 'Guardrail Blocked' : 'Guardrail', hint: guardrailState === 'blocked' ? 'Action not permitted' : 'Policy evaluation', state: guardrailState },
    { key: 'approval', label: 'Merchant Approval', hint: 'Mandatory — no auto-execute', state: approvalState },
    { key: 'execution', label: 'TEST MODE Execution', hint: 'Razorpay Test Mode only', state: execState },
    { key: 'measure', label: 'Measurement', hint: 'Outcome recorded', state: measureState },
  ]

  return (
    <div className="guardrail-flow" role="list" aria-label="Guardrail and approval flow">
      {steps.map((s) => (
        <div className={stepClass(s.state)} key={s.key} role="listitem">
          <Dot state={s.state} />
          <b>{s.label}</b>
          <small>{s.hint}</small>
        </div>
      ))}
    </div>
  )
}

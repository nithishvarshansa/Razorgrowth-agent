import { IconAlert, IconRefresh } from './icons'

// Every fact shown here comes from real application state — the caught checkout
// error, the guardrail/approval state already on screen, or a real payment_failed /
// payment_cancelled measurement event the backend already recorded. Nothing is
// simulated: this panel only renders when an actual execution attempt did not
// verify, and it never claims the AI retried or executed anything on its own.
export default function FailureRecovery({ recommendationId, reason, guardrailDecision, approvalStatus, duplicateBlocked, onRecover, recovering, recoveryAvailable }) {
  return (
    <div className="failure-recovery card card-pad" role="alert">
      <div className="fr-head">
        <span className="fr-icon"><IconAlert width={18} height={18} /></span>
        <div>
          <h3>Execution failed</h3>
          <span className="section-sub">TEST MODE — no funds moved</span>
        </div>
      </div>

      <div className="fr-reason">
        <b>Reason</b>
        <p>{reason || 'No failure reason was returned by the application.'}</p>
      </div>

      <div className="fr-response">
        <b>AI response</b>
        <ul>
          <li>Failure detected{recommendationId ? ` for recommendation ${recommendationId}` : ''}</li>
          <li>{duplicateBlocked ? 'Duplicate execution blocked by the existing Test Mode order guard' : 'No duplicate order was created'}</li>
          <li>Original decision preserved — merchant decision: {approvalStatus || 'unknown'}</li>
          <li>Guardrail remains active — last decision: {guardrailDecision ? guardrailDecision.replace(/_/g, ' ') : 'unchanged'}</li>
          <li>{recoveryAvailable ? 'Recovery action generated' : 'Recovery action not yet requested'}</li>
        </ul>
      </div>

      <div className="fr-next">
        <b>Next safe action</b>
        <p>The agent does not retry automatically. Re-run ranking to see whether a different eligible opportunity exists — the failed action stays recorded and excluded.</p>
        <button className="btn btn-secondary" disabled={recovering} onClick={onRecover}>
          {recovering && <span className="spinner" />}<IconRefresh width={14} height={14} />{recovering ? 'Re-ranking…' : 'Generate Next Action'}
        </button>
        <small className="fr-approval-note">Merchant approval required before any next action executes.</small>
      </div>
    </div>
  )
}

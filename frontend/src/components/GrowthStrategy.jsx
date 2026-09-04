import { useEffect, useRef, useState } from 'react'
import {
  addMeasurementEvent, approveRecommendation, createDemoRecommendation, createTestOrder, evaluateGuardrail,
  getMeasurement, rejectRecommendation, runGrowthAgent, syncTestModeData,
} from '../services/api'
import { openTestCheckout } from '../services/razorpayCheckout'
import AIVisualization from './AIVisualization'
import AgentTimeline from './AgentTimeline'
import DecisionCenter from './DecisionCenter'
import EvidenceTrail from './EvidenceTrail'
import FailureRecovery from './FailureRecovery'
import GrowthRoadmap from './GrowthRoadmap'
import GuardrailFlow from './GuardrailFlow'
import OpportunityPipeline from './OpportunityPipeline'
import Reasoning from './Reasoning'
import { IconBolt, IconChevron } from './icons'

function ErrorBox({ error }) {
  return <div className="error-box">{error.message || 'Unable to load data. Please try again.'}</div>
}

export default function GrowthStrategy() {
  const [demo, setDemo] = useState(null)
  const [guardrail, setGuardrail] = useState(null)
  const [commerce, setCommerce] = useState(null)
  const [measurement, setMeasurement] = useState(null)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const [checkoutMsg, setCheckoutMsg] = useState('')
  const [nextAction, setNextAction] = useState(null)
  const [nextGuardrail, setNextGuardrail] = useState(null)
  const [syncResult, setSyncResult] = useState(null)
  const [executionError, setExecutionError] = useState(null)
  const [nextCommerce, setNextCommerce] = useState(null)
  const [nextMeasurement, setNextMeasurement] = useState(null)
  const [nextCheckoutMsg, setNextCheckoutMsg] = useState('')
  const [nextExecutionError, setNextExecutionError] = useState(null)
  const [dcFocus, setDcFocus] = useState(false)
  const decisionCenterRef = useRef(null)
  const dcFocusTimerRef = useRef(null)

  const refreshMeasurement = async (id) => { try { setMeasurement(await getMeasurement(id)) } catch { /* non-fatal for the demo timeline */ } }
  const refreshNextMeasurement = async (id) => { try { setNextMeasurement(await getMeasurement(id)) } catch { /* non-fatal for the demo timeline */ } }

  const runDemo = async () => {
    setBusy('run'); setError(null); setGuardrail(null); setCommerce(null); setMeasurement(null); setCheckoutMsg(''); setNextAction(null); setNextGuardrail(null); setExecutionError(null)
    try {
      const rec = await createDemoRecommendation(); setDemo(rec)
      await refreshMeasurement(rec.agent_run_id)
      setBusy('evaluate')
      const decision = await evaluateGuardrail(rec.agent_run_id); setGuardrail(decision)
      await refreshMeasurement(rec.agent_run_id)
    } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const decide = async (action) => {
    setBusy(action); setError(null)
    try {
      const decision = action === 'approve' ? await approveRecommendation(demo.agent_run_id) : await rejectRecommendation(demo.agent_run_id)
      setGuardrail(decision)
      await refreshMeasurement(demo.agent_run_id)
    } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const startCheckout = async () => {
    setBusy('checkout'); setError(null); setExecutionError(null); setCheckoutMsg('Creating TEST MODE order…')
    try {
      const order = await createTestOrder(demo.agent_run_id); setCommerce(order)
      await refreshMeasurement(demo.agent_run_id)
      setCheckoutMsg('Opening TEST MODE checkout…')
      await openTestCheckout(order)
      setCheckoutMsg('Payment verified — TEST MODE only, no real funds moved.')
      await refreshMeasurement(demo.agent_run_id)
    } catch (e) {
      setCheckoutMsg('Payment not completed: ' + e.message)
      // A cancelled Test Mode checkout never reaches the backend, so it is
      // recorded here via the existing generic measurement endpoint — the
      // duplicate-order and signature-failure cases are already recorded
      // server-side and picked up by refreshMeasurement below.
      if (e.message === 'Test checkout was cancelled.') {
        try { await addMeasurementEvent(demo.agent_run_id, 'payment_cancelled', { reason: e.message }) } catch { /* best-effort audit trail only */ }
      }
      await refreshMeasurement(demo.agent_run_id)
      setExecutionError({ message: e.message, status: e.status, duplicate: e.status === 409 })
    } finally { setBusy(null) }
  }
  const generateNext = async () => {
    setBusy('next'); setError(null); setNextGuardrail(null); setNextCommerce(null); setNextMeasurement(null); setNextCheckoutMsg(''); setNextExecutionError(null)
    try { setNextAction(await runGrowthAgent()) } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const syncTestData = async () => {
    setBusy('sync'); setError(null)
    try {
      setSyncResult(await syncTestModeData())
      setNextGuardrail(null); setNextCommerce(null); setNextMeasurement(null); setNextCheckoutMsg(''); setNextExecutionError(null)
      setNextAction(await runGrowthAgent())
    } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const evaluateNext = async () => {
    setBusy('next-evaluate'); setError(null)
    try { setNextGuardrail(await evaluateGuardrail(nextAction.agent_run_id)) } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const decideNext = async (action) => {
    setBusy('next-' + action); setError(null)
    try { setNextGuardrail(action === 'approve' ? await approveRecommendation(nextAction.agent_run_id) : await rejectRecommendation(nextAction.agent_run_id)) } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const startNextCheckout = async () => {
    setBusy('next-checkout'); setError(null); setNextExecutionError(null); setNextCheckoutMsg('Creating TEST MODE order…')
    try {
      const order = await createTestOrder(nextAction.agent_run_id); setNextCommerce(order)
      await refreshNextMeasurement(nextAction.agent_run_id)
      setNextCheckoutMsg('Opening TEST MODE checkout…')
      await openTestCheckout(order)
      setNextCheckoutMsg('Payment verified — TEST MODE only, no real funds moved.')
      await refreshNextMeasurement(nextAction.agent_run_id)
    } catch (e) {
      setNextCheckoutMsg('Payment not completed: ' + e.message)
      if (e.message === 'Test checkout was cancelled.') {
        try { await addMeasurementEvent(nextAction.agent_run_id, 'payment_cancelled', { reason: e.message }) } catch { /* best-effort audit trail only */ }
      }
      await refreshNextMeasurement(nextAction.agent_run_id)
      setNextExecutionError({ message: e.message, status: e.status, duplicate: e.status === 409 })
    } finally { setBusy(null) }
  }

  const approved = guardrail?.status === 'approved'
  const rejected = guardrail?.status === 'rejected'
  const pendingApproval = guardrail?.status === 'pending_approval'
  const blocked = guardrail?.decision === 'blocked' || guardrail?.decision === 'insufficient_evidence'
  const paymentVerified = (measurement?.events || []).some((e) => e.event_type === 'payment_verified')

  // A real, backend-recorded failure event takes priority over the transient
  // client-side error, since it is durable and reflects what the application
  // actually persisted; the caught error is the fallback when the failure
  // never reached the backend (e.g. a cancelled checkout modal).
  const failureEvent = [...(measurement?.events || [])].reverse().find((e) => e.event_type === 'payment_failed' || e.event_type === 'payment_cancelled')
  const executionFailed = approved && !paymentVerified && (!!failureEvent || !!executionError)
  const failureReason = failureEvent?.metadata?.reason || failureEvent?.metadata?.detail || executionError?.message || ''
  const duplicateBlocked = !!executionError?.duplicate

  const nextEligible = nextAction?.status === 'recommended'
  const nextApproved = nextGuardrail?.status === 'approved'
  const nextRejected = nextGuardrail?.status === 'rejected'
  const nextBlocked = nextGuardrail?.decision === 'blocked' || nextGuardrail?.decision === 'insufficient_evidence'
  const nextSelectedKey = nextEligible ? `${nextAction.customer_id}|${nextAction.recommended_product}|${nextAction.opportunity_type}` : null

  const nextPaymentVerified = (nextMeasurement?.events || []).some((e) => e.event_type === 'payment_verified')
  const nextFailureEvent = [...(nextMeasurement?.events || [])].reverse().find((e) => e.event_type === 'payment_failed' || e.event_type === 'payment_cancelled')
  const nextExecutionFailed = nextApproved && !nextPaymentVerified && (!!nextFailureEvent || !!nextExecutionError)
  const nextFailureReason = nextFailureEvent?.metadata?.reason || nextFailureEvent?.metadata?.detail || nextExecutionError?.message || ''
  const nextDuplicateBlocked = !!nextExecutionError?.duplicate
  // Once this recommendation's outcome is fully known (executed, rejected, blocked, or
  // failed), the closed loop can continue — re-using the same real /api/agent/run call.
  const nextConcluded = nextPaymentVerified || nextRejected || nextBlocked || nextExecutionFailed

  // Read-only selection for the Smart Growth Roadmap: whichever cycle (the
  // original demo, or the next action once it becomes eligible) is the
  // "active" one to summarize — the same selection GrowthStrategy already
  // makes inline for the hero card above. This never mutates state.
  const roadmapRecommendation = nextEligible ? nextAction : demo
  const roadmapGuardrail = nextEligible ? nextGuardrail : guardrail
  const roadmapApproved = nextEligible ? nextApproved : approved
  const roadmapRejected = nextEligible ? nextRejected : rejected
  const roadmapBlocked = nextEligible ? nextBlocked : blocked
  const roadmapPendingApproval = roadmapGuardrail?.status === 'pending_approval'
  const roadmapCommerce = nextEligible ? nextCommerce : commerce
  const roadmapPaymentVerified = nextEligible ? nextPaymentVerified : paymentVerified
  const roadmapExecutionFailed = nextEligible ? nextExecutionFailed : executionFailed
  const roadmapFailureReason = nextEligible ? nextFailureReason : failureReason

  // Bring the Decision Center into view only on a real, meaningful state
  // transition (never on mount, never for unrelated re-renders) so the
  // merchant can see the stage that just changed without scrolling manually.
  // Purely presentational — it reads state, it never writes it.
  const scrollToDecisionCenter = () => {
    const el = decisionCenterRef.current
    if (!el) return
    const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' })
    setDcFocus(true)
    if (dcFocusTimerRef.current) clearTimeout(dcFocusTimerRef.current)
    dcFocusTimerRef.current = setTimeout(() => setDcFocus(false), 1200)
  }
  useEffect(() => { if (demo) scrollToDecisionCenter() }, [demo?.agent_run_id])
  useEffect(() => { if (approved) scrollToDecisionCenter() }, [approved])
  useEffect(() => { if (rejected) scrollToDecisionCenter() }, [rejected])
  useEffect(() => { if (paymentVerified) scrollToDecisionCenter() }, [paymentVerified])
  useEffect(() => { if (executionFailed) scrollToDecisionCenter() }, [executionFailed])
  useEffect(() => { if (nextAction) scrollToDecisionCenter() }, [nextAction?.agent_run_id])
  useEffect(() => () => { if (dcFocusTimerRef.current) clearTimeout(dcFocusTimerRef.current) }, [])

  // Every state below is derived from real fields already returned by the backend, or
  // from the exact `busy` marker already set around a real in-flight network call —
  // nothing here is a scripted animation or a timer independent of actual application
  // state. 'active' means a real request for THIS stage is currently in flight;
  // 'pending' means the stage has been reached but is genuinely waiting on the
  // merchant to act (not the system computing); 'skipped' means this run's real
  // outcome (e.g. a merchant rejection) makes the stage genuinely not applicable.
  const rankedCount = demo?.ranked_opportunities?.length || 0
  const checkoutInFlight = busy === 'checkout'
  const decisionStages = [
    { key: 'analyze', label: 'Analyze', hint: demo ? (demo.observed_facts?.[0] || 'Stored data observed') : busy === 'run' ? 'Observing stored Test Mode data…' : 'Waiting to run', state: demo ? 'done' : busy === 'run' ? 'active' : '' },
    { key: 'discover', label: 'Discover', hint: demo ? `${demo.opportunity_type?.replace('_', ' ') || 'Opportunity'} signal identified` : '', state: demo ? 'done' : '' },
    { key: 'rank', label: 'Rank', hint: demo ? (rankedCount > 1 ? `${rankedCount} opportunities compared` : 'Isolated demo fixture — single option') : '', state: demo ? 'done' : '' },
    { key: 'select', label: 'Select', hint: demo ? (demo.status === 'recommended' ? `Selected ${demo.recommended_product}` : 'No eligible opportunity') : '', state: demo?.status === 'recommended' ? 'done' : demo ? 'blocked' : '' },
    { key: 'explain', label: 'Explain', hint: demo?.reasoning ? (demo.expected_outcome ? 'Reasoning + hypothesis generated' : 'Reasoning generated') : '', state: demo?.reasoning ? 'done' : '' },
    { key: 'guardrail', label: 'Guardrail', hint: guardrail ? guardrail.decision.replace(/_/g, ' ') : busy === 'evaluate' ? 'Evaluating policy…' : '', state: guardrail ? (guardrail.decision === 'allowed_for_approval' ? 'done' : 'blocked') : busy === 'evaluate' ? 'active' : '' },
    {
      key: 'merchant', label: 'Merchant',
      hint: approved ? 'Approved' : rejected ? 'Rejected by merchant' : (busy === 'approve' || busy === 'reject') ? 'Recording merchant decision…' : pendingApproval ? 'Waiting for merchant decision' : '',
      state: approved || rejected ? 'done' : (busy === 'approve' || busy === 'reject') ? 'active' : pendingApproval ? 'pending' : '',
    },
    {
      key: 'execute', label: 'Execute',
      hint: paymentVerified ? 'TEST MODE order executed' : executionFailed ? (failureReason || 'Execution failed') : rejected ? 'Not executed — rejected by merchant' : checkoutInFlight ? 'Creating Test Mode order / awaiting checkout…' : approved ? 'Waiting for merchant to start Test Mode checkout' : '',
      state: paymentVerified ? 'done' : executionFailed ? 'failed' : rejected ? 'skipped' : checkoutInFlight ? 'active' : approved ? 'pending' : '',
    },
    {
      key: 'measure', label: 'Measure',
      hint: paymentVerified ? 'Outcome recorded' : executionFailed ? 'Failure recorded' : rejected ? 'Not applicable' : checkoutInFlight ? 'Awaiting payment outcome…' : '',
      state: paymentVerified ? 'done' : executionFailed ? 'done' : rejected ? 'skipped' : checkoutInFlight ? 'active' : '',
    },
    {
      key: 'next', label: 'Next Action', loop: true,
      hint: nextAction ? 'Decision memory updated' : busy === 'next' ? 'Re-ranking remaining opportunities…' : executionFailed ? 'Recovery ready — waiting for merchant' : (paymentVerified || rejected || blocked) ? 'Ready — waiting for merchant to re-rank' : '',
      state: nextAction ? 'done' : busy === 'next' ? 'active' : (paymentVerified || rejected || blocked || executionFailed) ? 'pending' : '',
    },
  ]

  return (
    <section id="growth-strategy" className="page-section enter">
      <div className="hero">
        <div className="hero-left">
          <span className="hero-eyebrow"><IconBolt width={13} height={13} /> AI Growth Strategy</span>
          <h1>Your next growth action,<br />selected by evidence.</h1>
          <p className="lead">The Growth Agent observes stored Test Mode data, ranks eligible opportunities, and explains why one was selected — it never executes a payment action on its own.</p>

          {!demo && !nextAction && (
            <div className="hero-cta" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
              <button className="btn btn-primary" disabled={busy === 'run'} onClick={runDemo}>
                {busy === 'run' && <span className="spinner" />}{busy === 'run' ? 'Running…' : 'Run Growth Demo'}
              </button>
              {busy === 'run' && <small style={{ color: '#a9a4d6', fontSize: 12 }}>Analyzing merchant data…</small>}
            </div>
          )}

          {(demo || nextEligible) && (() => {
            const rec = nextEligible ? nextAction : demo
            const rgGuardrail = nextEligible ? nextGuardrail : guardrail
            return (
              <div className="ai-card">
                <span className="ai-tag">AI Growth Recommendation</span>
                <div className="flow">
                  <small>{rec.opportunity_type?.replace('_', ' ')}</small>
                  {rec.recommended_product}
                </div>
                <div className="pill-row">
                  <span className={'pill ' + (rec.opportunity_type === 'upsell' ? 'info' : 'success')}>{rec.opportunity_type?.replace('_', ' ')}</span>
                  {rec.priority && <span className={'pill ' + (rec.priority === 'HIGH' ? 'ok' : rec.priority === 'MEDIUM' ? 'warn' : 'neutral')}>{rec.priority} priority</span>}
                  <span className="pill neutral">{rec.confidence || '--'} confidence</span>
                  {rgGuardrail && <span className={'pill ' + (rgGuardrail.decision === 'allowed_for_approval' ? 'ok' : 'bad')}>{rgGuardrail.decision.replace(/_/g, ' ')}</span>}
                </div>
                <p className="why">"{rec.inferred_insight || rec.reasoning}"</p>
                <EvidenceTrail observedFacts={rec.observed_facts} evidence={rec.evidence} opportunityType={rec.opportunity_type} recommendedProduct={rec.recommended_product} />
                <a className="review-link" href="#safety-panel">Review recommendation <IconChevron width={13} height={13} /></a>
              </div>
            )
          })()}
        </div>
        <div className="hero-right">
          {(demo || nextAction) ? <AIVisualization active /> : (
            <div className="hero-empty">
              <h3>No recommendation yet</h3>
              <p>Run the Growth Demo to see merchant data flow through AI analysis into a ranked, evidence-based opportunity.</p>
            </div>
          )}
        </div>
      </div>

      <GrowthRoadmap
        recommendation={roadmapRecommendation}
        guardrail={roadmapGuardrail}
        approved={roadmapApproved}
        rejected={roadmapRejected}
        blocked={roadmapBlocked}
        pendingApproval={roadmapPendingApproval}
        commerce={roadmapCommerce}
        paymentVerified={roadmapPaymentVerified}
        executionFailed={roadmapExecutionFailed}
        failureReason={roadmapFailureReason}
        nextAction={nextAction}
        nextEligible={nextEligible}
      />

      {!demo && (
        <div ref={decisionCenterRef} className={dcFocus ? 'dc-focus' : ''} style={{ marginTop: 20 }}>
          <DecisionCenter stages={decisionStages} revealKey={null} />
        </div>
      )}

      {demo && (
        <div className="rec-grid" style={{ marginTop: 20 }}>
        <div id="safety-panel" className="card card-pad" style={{ scrollMarginTop: 92 }}>
          <div className="section-head" style={{ marginBottom: 14 }}>
            <h2>AI Recommendation</h2>
          </div>

          {guardrail && (
            <div className="rec-section guardrail">
              <div className="rec-label"><IconBolt width={11} height={11} /> Guardrail</div>
              <p>{guardrail.decision.replace(/_/g, ' ')}{guardrail.reasons?.length ? ' — ' + guardrail.reasons.join('; ') : ' — evidence, product, and value checks passed'}</p>
            </div>
          )}
          {demo.expected_outcome && (
            <div className="rec-section hypothesis">
              <div className="rec-label"><IconBolt width={11} height={11} /> AI Growth Experiment · Hypothesis</div>
              <p>{demo.expected_outcome}</p>
            </div>
          )}

          <Reasoning
            reasoning={demo.reasoning}
            evidence={demo.evidence}
            confidence={demo.confidence}
            priority={demo.priority}
            objective={demo.recommendation}
            expectedOutcome={demo.expected_outcome}
            guardrailLabel={guardrail ? guardrail.decision.replace(/_/g, ' ') : undefined}
            guardrailTone={guardrail ? (guardrail.decision === 'allowed_for_approval' ? 'ok' : 'bad') : undefined}
          />

          {pendingApproval && (
            <div className="actions" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" disabled={!!busy} onClick={() => decide('approve')}>
                {busy === 'approve' && <span className="spinner" />}{busy === 'approve' ? 'Approving…' : 'Approve & Continue'}
              </button>
              <button className="btn btn-danger" disabled={!!busy} onClick={() => decide('reject')}>
                {busy === 'reject' ? 'Rejecting…' : 'Reject'}
              </button>
            </div>
          )}
          {blocked && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>Guardrail policy did not permit this opportunity for approval — no Test Mode action is possible.</p>}
          {rejected && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>Rejected by merchant. No Test Mode order was created and no payment occurred.</p>}

          {approved && (
            <div style={{ marginTop: 16 }}>
              {!paymentVerified && (
                <button className="btn btn-primary" disabled={busy === 'checkout'} onClick={startCheckout}>
                  {busy === 'checkout' && <span className="spinner" />}{busy === 'checkout' ? 'Working…' : 'Create Test Order & Open Checkout'}
                </button>
              )}
              {commerce && <p className="evidence" style={{ marginTop: 10 }}>Test Mode order {commerce.razorpay_order_id} · {commerce.amount != null ? `${commerce.amount / 100} ${commerce.currency}` : ''}</p>}
              {checkoutMsg && <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>{checkoutMsg}</p>}
              {!paymentVerified && !checkoutMsg && <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>No real payment has occurred yet.</p>}
            </div>
          )}

          {executionFailed && (
            <div style={{ marginTop: 16 }}>
              <FailureRecovery
                recommendationId={demo.agent_run_id}
                reason={failureReason}
                guardrailDecision={guardrail?.decision}
                approvalStatus={guardrail?.status}
                duplicateBlocked={duplicateBlocked}
                recoveryAvailable={!!nextAction}
                recovering={busy === 'next'}
                onRecover={generateNext}
              />
            </div>
          )}

          <AgentTimeline measurement={measurement} pendingLabel={approved && !paymentVerified ? 'Payment verification' : undefined} />
        </div>

        <div ref={decisionCenterRef} className={dcFocus ? 'dc-focus' : ''}>
          <DecisionCenter stages={decisionStages} revealKey={demo.agent_run_id} />
        </div>
        </div>
      )}

      {demo && (
        <div className="card card-pad" style={{ marginTop: 20 }}>
          <div className="section-head" style={{ marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
            <h2>Approval flow progress</h2>
            <span className="safety-principle">
              <b>AI recommends</b><span className="sp-arrow">→</span><b>Merchant decides</b><span className="sp-arrow">→</span><b>Razorpay executes</b>
            </span>
          </div>
          <GuardrailFlow
            hasRecommendation={!!demo}
            guardrailEvaluated={!!guardrail}
            guardrailPassed={guardrail?.decision === 'allowed_for_approval'}
            approvalStatus={approved ? 'approved' : rejected ? 'rejected' : pendingApproval ? 'pending' : null}
            executed={paymentVerified}
            measured={paymentVerified}
          />
        </div>
      )}

      {guardrail && (paymentVerified || rejected || blocked || executionFailed) && (
        <div className="card card-pad" style={{ marginTop: 20 }}>
          <div className="section-head" style={{ marginBottom: 6 }}>
            <h2>Next action</h2>
            <span className="section-sub">Re-ranks remaining opportunities, excluding what's already decided</span>
          </div>
          {!nextAction && (
            <>
              <div className="pipeline-tags" style={{ marginBottom: 14 }}>
                <span className="pill success">Decision recorded</span>
                <span className="pill info">Decision memory updated</span>
                <span className="pill neutral">Ready to re-rank</span>
              </div>
              <button className="btn btn-primary" disabled={busy === 'next'} onClick={generateNext}>
                {busy === 'next' && <span className="spinner" />}{busy === 'next' ? 'Re-ranking…' : 'Generate Next Action'}
              </button>
            </>
          )}
          {nextAction && !nextEligible && (
            <div className="empty" style={{ marginTop: 4 }}>
              <h3>No new eligible action</h3>
              <p>{nextAction.reasoning}</p>
              {!nextAction.reasoning?.toLowerCase().includes('already been decided') && (
                <>
                  <p style={{ marginTop: 10 }}>
                    The opportunity engine needs at least two successful (captured), product-identified Test Mode
                    purchases — from stored Razorpay Test Mode orders and payments — to detect an upsell or cross-sell
                    pattern. This demo's own Test Mode checkout does not attach product/customer notes to the order it
                    creates, so it cannot supply this by itself.
                  </p>
                  <button className="btn btn-secondary" disabled={busy === 'sync'} onClick={syncTestData}>
                    {busy === 'sync' && <span className="spinner" />}{busy === 'sync' ? 'Syncing Test Mode data…' : 'Sync Test Mode Data'}
                  </button>
                  {syncResult && (
                    <p style={{ marginTop: 10, fontSize: 12.5 }}>
                      Synced {syncResult.normalized_orders} order{syncResult.normalized_orders === 1 ? '' : 's'} and {syncResult.normalized_payments} payment{syncResult.normalized_payments === 1 ? '' : 's'} from Razorpay Test Mode. Re-ran the agent — still no eligible opportunity, so the required purchase pattern isn't present in your Test Mode account yet.
                    </p>
                  )}
                </>
              )}
            </div>
          )}
          {nextEligible && (
            <>
              {nextAction.observed_facts?.some((f) => f.toLowerCase().includes('excluded')) && (
                <p className="reasoning-evidence" style={{ marginBottom: 10 }}>
                  {nextAction.observed_facts.find((f) => f.toLowerCase().includes('excluded'))}
                </p>
              )}
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 12px' }}>{(nextAction.ranked_opportunities || []).length} opportunit{(nextAction.ranked_opportunities || []).length === 1 ? 'y' : 'ies'} found from stored Test Mode data</p>
              <OpportunityPipeline opportunities={nextAction.ranked_opportunities} selectedKey={nextSelectedKey} />
              {nextGuardrail && (
                <div className="rec-section guardrail">
                  <div className="rec-label"><IconBolt width={11} height={11} /> Guardrail</div>
                  <p>{nextGuardrail.decision.replace(/_/g, ' ')}{nextGuardrail.reasons?.length ? ' — ' + nextGuardrail.reasons.join('; ') : ' — evidence, product, and value checks passed'}</p>
                </div>
              )}
              {nextAction.expected_outcome && (
                <div className="rec-section hypothesis">
                  <div className="rec-label"><IconBolt width={11} height={11} /> AI Growth Experiment · Hypothesis</div>
                  <p>{nextAction.expected_outcome}</p>
                </div>
              )}
              <Reasoning
                reasoning={nextAction.reasoning}
                evidence={nextAction.evidence}
                confidence={nextAction.confidence}
                priority={nextAction.priority}
                objective={nextAction.recommendation}
                expectedOutcome={nextAction.expected_outcome}
                guardrailLabel={nextGuardrail ? nextGuardrail.decision.replace(/_/g, ' ') : undefined}
                guardrailTone={nextGuardrail ? (nextGuardrail.decision === 'allowed_for_approval' ? 'ok' : 'bad') : undefined}
              />
              {!nextGuardrail && (
                <div className="actions" style={{ marginTop: 14 }}>
                  <button className="btn btn-secondary" disabled={busy === 'next-evaluate'} onClick={evaluateNext}>
                    {busy === 'next-evaluate' ? 'Evaluating…' : 'Evaluate Guardrail'}
                  </button>
                </div>
              )}
              {nextGuardrail?.status === 'pending_approval' && (
                <div className="actions" style={{ marginTop: 14 }}>
                  <button className="btn btn-primary" disabled={!!busy} onClick={() => decideNext('approve')}>{busy === 'next-approve' ? 'Approving…' : 'Approve & Continue'}</button>
                  <button className="btn btn-danger" disabled={!!busy} onClick={() => decideNext('reject')}>{busy === 'next-reject' ? 'Rejecting…' : 'Reject'}</button>
                </div>
              )}
              {nextRejected && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>Rejected by merchant. No Test Mode order was created and no payment occurred.</p>}
              {nextBlocked && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>Guardrail policy did not permit this opportunity for approval — no Test Mode action is possible.</p>}

              {nextApproved && (
                <div style={{ marginTop: 16 }}>
                  {!nextPaymentVerified && (
                    <button className="btn btn-primary" disabled={busy === 'next-checkout'} onClick={startNextCheckout}>
                      {busy === 'next-checkout' && <span className="spinner" />}{busy === 'next-checkout' ? 'Working…' : 'Create Test Order & Open Checkout'}
                    </button>
                  )}
                  {nextCommerce && <p className="evidence" style={{ marginTop: 10 }}>Test Mode order {nextCommerce.razorpay_order_id} · {nextCommerce.amount != null ? `${nextCommerce.amount / 100} ${nextCommerce.currency}` : ''}</p>}
                  {nextCheckoutMsg && <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>{nextCheckoutMsg}</p>}
                  {!nextPaymentVerified && !nextCheckoutMsg && <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>No real payment has occurred yet.</p>}
                </div>
              )}

              {nextExecutionFailed && (
                <div style={{ marginTop: 16 }}>
                  <FailureRecovery
                    recommendationId={nextAction.agent_run_id}
                    reason={nextFailureReason}
                    guardrailDecision={nextGuardrail?.decision}
                    approvalStatus={nextGuardrail?.status}
                    duplicateBlocked={nextDuplicateBlocked}
                    recoveryAvailable={false}
                    recovering={busy === 'next'}
                    onRecover={generateNext}
                  />
                </div>
              )}

              <AgentTimeline measurement={nextMeasurement} pendingLabel={nextApproved && !nextPaymentVerified ? 'Payment verification' : undefined} />

              {nextConcluded && (
                <div className="actions" style={{ marginTop: 16 }}>
                  <button className="btn btn-primary" disabled={busy === 'next'} onClick={generateNext}>
                    {busy === 'next' && <span className="spinner" />}{busy === 'next' ? 'Re-ranking…' : 'Generate Next Action'}
                  </button>
                  <small style={{ color: 'var(--text-faint)', display: 'block', marginTop: 8 }}>This decision is now recorded and excluded — re-ranking will surface the next eligible opportunity, if any.</small>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {error && <div style={{ marginTop: 16 }}><ErrorBox error={error} /></div>}
    </section>
  )
}

const EVENT_LABELS = {
  recommendation_created: 'Recommendation created',
  guardrail_evaluated: 'Evidence evaluated · Guardrail evaluated',
  merchant_approved: 'Merchant approved',
  merchant_rejected: 'Merchant rejected',
  test_order_created: 'TEST MODE order created',
  checkout_started: 'Checkout started',
  payment_attempted: 'Payment attempted',
  payment_verified: 'Payment verified',
  payment_failed: 'Payment failed',
  payment_cancelled: 'Payment cancelled',
}

export default function AgentTimeline({ measurement, pendingLabel }) {
  const events = measurement?.events || []
  if (!events.length && !pendingLabel) return null
  return (
    <div className="timeline">
      {events.length > 0 && <h4 style={{ fontSize: 12.5, textTransform: 'uppercase', letterSpacing: '.07em', color: 'var(--text-faint)', margin: '4px 0 2px' }}>Agent activity</h4>}
      {events.map((e) => (
        <div className="step done" key={e.event_id}>
          <span className="dot">●</span>
          <div>
            <b>{EVENT_LABELS[e.event_type] || e.event_type}</b>
            <small>{new Date(e.timestamp).toLocaleTimeString()} · {e.mode}</small>
          </div>
        </div>
      ))}
      {pendingLabel && (
        <div className="step pending">
          <span className="dot">○</span>
          <div><b>{pendingLabel}</b><small>Pending</small></div>
        </div>
      )}
    </div>
  )
}

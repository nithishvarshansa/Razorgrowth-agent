export default function Reasoning({ reasoning, evidence, confidence, priority, objective, guardrailLabel, guardrailTone, expectedOutcome }) {
  return (
    <details className="reasoning">
      <summary>Why this recommendation?</summary>
      <div className="reasoning-body">
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>{reasoning}</p>
        {evidence?.length > 0 && (
          <div>
            {evidence.map((e, i) => <p className="reasoning-evidence" key={i}>{e}</p>)}
          </div>
        )}
        {expectedOutcome && (
          <div>
            <small style={{ display: 'block', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.04em', color: 'var(--text-faint)', marginBottom: 4 }}>AI hypothesis · expected outcome</small>
            <p className="reasoning-evidence">{expectedOutcome}</p>
          </div>
        )}
        <div>
          {confidence && <div className="reasoning-row"><span>Confidence</span><span>{confidence}</span></div>}
          {priority && <div className="reasoning-row"><span>Priority</span><span><span className={'pill ' + (priority === 'HIGH' ? 'ok' : priority === 'MEDIUM' ? 'warn' : 'neutral')}>{priority}</span></span></div>}
          {guardrailLabel && <div className="reasoning-row"><span>Guardrail status</span><span><span className={'pill ' + (guardrailTone || 'neutral')}>{guardrailLabel}</span></span></div>}
          {objective && <div className="reasoning-row"><span>Expected objective</span><span>{objective}</span></div>}
        </div>
      </div>
    </details>
  )
}

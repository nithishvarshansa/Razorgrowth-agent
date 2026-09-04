import { useEffect, useRef, useState } from 'react'
import { IconBolt, IconCheck, IconClock } from './icons'

// Only these leading stages are ever visually staggered — they are the ones
// that can arrive "all at once" from a single atomic backend response. Every
// stage after them (merchant, execute, measure, next) always renders its real
// state immediately: a merchant decision, an execution result, or a failure
// must never be delayed behind a presentational animation.
const STAGGER_KEYS = ['analyze', 'discover', 'rank', 'select', 'explain', 'guardrail']
const STEP_MS = 250

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function Marker({ state, loop }) {
  if (loop) return <span className="dc-marker">↺</span>
  if (state === 'done') return <span className="dc-marker"><IconCheck width={14} height={14} /></span>
  if (state === 'blocked' || state === 'failed') return <span className="dc-marker">✗</span>
  if (state === 'pending') return <span className="dc-marker"><IconClock width={13} height={13} /></span>
  if (state === 'skipped') return <span className="dc-marker">—</span>
  return <span className="dc-marker" />
}

function stageClass(state) {
  if (state === 'done') return 'dc-stage done'
  if (state === 'active') return 'dc-stage active'
  if (state === 'failed') return 'dc-stage failed'
  if (state === 'blocked') return 'dc-stage blocked'
  if (state === 'pending') return 'dc-stage pending'
  if (state === 'skipped') return 'dc-stage skipped'
  return 'dc-stage'
}

// How many of the leading STAGGER_KEYS are currently 'done', counting only a
// contiguous run from the start — this is the real, already-known result; the
// reveal state below only controls WHEN that already-known result is shown.
function doneStaggerCount(stages) {
  let count = 0
  for (const key of STAGGER_KEYS) {
    const stage = stages.find((s) => s.key === key)
    if (stage?.state === 'done') count += 1
    else break
  }
  return count
}

export default function DecisionCenter({ stages, revealKey }) {
  const [revealedCount, setRevealedCount] = useState(0)
  const timerRef = useRef(null)

  // A new recommendation (or none at all) means the previous reveal sequence
  // no longer applies — cancel any pending step and start over from zero.
  useEffect(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }
    setRevealedCount(0)
  }, [revealKey])

  // Once a real DECISION or OUTCOME exists beyond the guardrail stage (approved,
  // rejected, an execution result, a failure, or a next action) the leading
  // reveal is no longer the important thing on screen — jump it straight to
  // complete instead of letting a cosmetic animation keep playing underneath an
  // already-real outcome. Merely *reaching* a stage (e.g. Merchant sitting at
  // 'pending', awaiting a click) is not a decision and must not trigger this.
  const decisionMade = stages.some((s) => ['merchant', 'execute', 'measure', 'next'].includes(s.key) && ['done', 'blocked', 'failed', 'skipped'].includes(s.state))
  const target = decisionMade ? STAGGER_KEYS.length : doneStaggerCount(stages)

  useEffect(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }

    if (revealedCount === target) return undefined

    // The real state moved past the point this animation still matters (a
    // merchant decision, execution result, or failure), or reduced motion is
    // requested — snap straight to the real result instead of animating.
    if (revealedCount > target || decisionMade || prefersReducedMotion()) {
      setRevealedCount(target)
      return undefined
    }

    const delay = revealedCount === 0 ? 0 : STEP_MS
    timerRef.current = setTimeout(() => setRevealedCount((c) => c + 1), delay)
    return () => { if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null } }
  }, [target, revealedCount])

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current) }, [])

  // Gate only a 'done' stagger-stage that hasn't had its turn yet — every other
  // state (active/pending/blocked/failed/skipped/'') always renders truthfully.
  const visibleStages = stages.map((s) => {
    const staggerIndex = STAGGER_KEYS.indexOf(s.key)
    if (staggerIndex !== -1 && s.state === 'done' && staggerIndex >= revealedCount) {
      return { ...s, state: '', hint: '' }
    }
    return s
  })

  return (
    <div className="decision-center">
      <div className="dc-head">
        <h2><IconBolt width={12} height={12} style={{ marginRight: 6, verticalAlign: -1 }} />AI Agent — Decision Center</h2>
        <span className="section-sub">Real agent state, not a simulation</span>
      </div>
      <div className="dc-stages" role="list" aria-label="Growth Agent decision lifecycle">
        {visibleStages.map((s, i) => (
          // The key includes the current state so that the moment a stage's
          // real (or now-revealed) state changes, React mounts a fresh node —
          // replaying the existing fade-up / check-pop entrance CSS below
          // rather than requiring any new animation machinery.
          <div className={stageClass(s.state) + (s.loop ? ' loop' : '')} style={{ animationDelay: `${i * 0.04}s` }} key={s.key + '-' + s.state} role="listitem">
            <Marker state={s.state} loop={s.loop} />
            <div className="dc-body">
              <b>{s.label}</b>
              {s.hint && <small>{s.hint}</small>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

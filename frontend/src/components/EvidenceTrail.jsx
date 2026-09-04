import { IconChevron } from './icons'

// Answers "where did this recommendation come from?" using only fields the
// backend already returned on the recommendation — nothing inferred or fabricated.
export default function EvidenceTrail({ observedFacts, evidence, opportunityType, recommendedProduct }) {
  return (
    <div>
      <div className="evidence-trail">
        <b>Merchant Data</b><IconChevron width={11} height={11} />
        <b>Evidence</b><IconChevron width={11} height={11} />
        <b>Opportunity</b><IconChevron width={11} height={11} />
        <b>Recommendation</b>
      </div>
      <div className="evidence-list">
        {observedFacts?.map((f, i) => <p className="reasoning-evidence" key={'o' + i}>{f}</p>)}
        {evidence?.map((e, i) => <p className="reasoning-evidence" key={'e' + i}>{e}</p>)}
        {opportunityType && recommendedProduct && (
          <p className="reasoning-evidence">→ {opportunityType.replace('_', ' ')}: {recommendedProduct}</p>
        )}
      </div>
    </div>
  )
}

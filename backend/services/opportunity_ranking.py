"""Ranks currently eligible growth opportunities so the agent can explain
which one to act on next.

Scoring is deterministic and derived only from fields the opportunity engine
and guardrail policy already produce (confidence, evidence volume, guardrail
eligibility, decision-memory exclusion). No opportunity, score, or evidence
is fabricated; when there is only one candidate the ranking simply confirms it.
"""
from typing import Any

from .guardrails import evaluate_recommendation

CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}
PRIORITY_LABEL = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
EVIDENCE_STRENGTH_LABEL = {"high": "Strong", "medium": "Moderate", "low": "Limited"}


def rank_opportunities(candidates: list[dict[str, Any]], exclude: set[tuple[str, str, str]] | None = None) -> list[dict[str, Any]]:
    """Score, guardrail-preview, and sort opportunities, highest-ranked first.

    score = confidence_weight * 10 + evidence_item_count
    Confidence dominates because it is the strongest signal the opportunity
    engine currently produces; the evidence item count is a secondary,
    same-confidence tiebreaker. Sorting is stable, so equally-scored
    opportunities keep the order the opportunity engine found them in.

    Already-decided opportunities (per the existing decision-memory exclusion
    set) and opportunities that would currently fail guardrail policy are
    ranked below eligible ones but are never hidden, so the merchant can see
    why an opportunity was or was not selected.
    """
    exclude = exclude or set()
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (candidate.get("customer_id"), candidate.get("recommended_product"), candidate.get("opportunity_type"))
        already_decided = key in exclude
        confidence = candidate.get("confidence") or "low"
        evidence = candidate.get("evidence") or []
        guardrail = evaluate_recommendation(candidate)
        eligible = guardrail.decision == "allowed_for_approval" and not already_decided
        score = CONFIDENCE_WEIGHT.get(confidence, 0) * 10 + len(evidence)
        ranked.append({
            **candidate,
            "score": score,
            "priority": PRIORITY_LABEL.get(confidence, "LOW"),
            "evidence_strength": EVIDENCE_STRENGTH_LABEL.get(confidence, "Limited"),
            "already_decided": already_decided,
            "eligible": eligible,
            "guardrail_decision": guardrail.decision,
            "guardrail_reasons": guardrail.reasons,
        })
    ranked.sort(key=lambda opportunity: (opportunity["eligible"], opportunity["score"]), reverse=True)
    return ranked

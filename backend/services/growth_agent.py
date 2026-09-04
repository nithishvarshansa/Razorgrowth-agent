from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..models.agent import AgentRecommendation
from .agent_provider import DeterministicDevelopmentProvider, GrowthAgentProvider
from .analytics import summarize
from .hypothesis import expected_outcome
from .opportunity_engine import analyze_opportunities
from .opportunity_ranking import rank_opportunities


class GrowthAgentService:
    def __init__(self, provider: GrowthAgentProvider | None = None) -> None:
        self._provider = provider or DeterministicDevelopmentProvider()

    def run(self, orders, payments, exclude: set[tuple[str, str, str]] | None = None) -> AgentRecommendation:
        started_at = datetime.now(UTC)
        analytics = summarize(orders, payments)
        opportunities = analyze_opportunities(orders, payments)
        all_candidates = opportunities.get("opportunities", [])
        ranked = rank_opportunities(all_candidates, exclude=exclude)
        remaining = [o for o in ranked if not o["already_decided"]]
        excluded_count = len(ranked) - len(remaining)
        candidate = self._provider.recommend({**opportunities, "opportunities": remaining}, analytics)
        ended_at = datetime.now(UTC)
        run_id = str(uuid4())
        observed_facts = [f"Stored orders: {analytics['orders']['count']}", f"Stored payments: {analytics['payments']['count']}"]
        if excluded_count:
            observed_facts.append(f"Excluded {excluded_count} opportunit{'y' if excluded_count == 1 else 'ies'} the merchant already decided on.")
        if not candidate:
            if excluded_count and not remaining and all_candidates:
                reason = "All evidence-supported opportunities have already been decided by the merchant; no new opportunity is available yet."
            else:
                reason = opportunities.get("reason") or "No supported opportunity was identified."
            return AgentRecommendation(agent_run_id=run_id, status="insufficient_evidence", mode="deterministic_development", started_at=started_at, ended_at=ended_at, observed_facts=observed_facts, reasoning=reason, ranked_opportunities=ranked)
        alternatives = [o for o in remaining if o is not candidate]
        return AgentRecommendation(
            agent_run_id=run_id, status="recommended", mode="deterministic_development",
            started_at=started_at, ended_at=ended_at,
            opportunity_type=candidate["opportunity_type"], customer_id=candidate["customer_id"], recommended_product=candidate["recommended_product"],
            observed_facts=observed_facts, inferred_insight=candidate["reason"],
            reasoning=_explain_selection(candidate, alternatives, excluded_count),
            evidence=candidate["evidence"], confidence=candidate["confidence"],
            recommendation=f"Review the {candidate['opportunity_type'].replace('_', ' ')} opportunity before any future action.",
            priority=candidate.get("priority"), ranked_opportunities=ranked,
            expected_outcome=expected_outcome(candidate["opportunity_type"]),
        )


def _explain_selection(candidate: dict[str, Any], alternatives: list[dict[str, Any]], excluded_count: int) -> str:
    label = candidate["opportunity_type"].replace("_", " ")
    if candidate.get("eligible"):
        parts = [f"Selected the {label} opportunity because it has the strongest available evidence (confidence: {candidate['confidence']}) among the currently eligible opportunities and is within the configured guardrails."]
    else:
        reasons = "; ".join(candidate.get("guardrail_reasons") or []) or "guardrail policy has not been evaluated yet"
        parts = [f"Selected the {label} opportunity as the highest-ranked available option; it is not yet guardrail-eligible ({reasons})."]
    if alternatives:
        parts.append(f"{len(alternatives)} other opportunit{'y is' if len(alternatives) == 1 else 'ies are'} available as alternatives.")
    if excluded_count:
        parts.append(f"{excluded_count} previously decided opportunit{'y was' if excluded_count == 1 else 'ies were'} excluded from consideration.")
    return " ".join(parts)

from typing import Any
from ..models.guardrails import GuardrailDecision, PolicyCheck

PERMITTED_ACTIONS = {"cross_sell_recommendation", "upsell_recommendation"}
MIN_CONFIDENCE = {"medium", "high"}
MAX_ESTIMATED_VALUE = 100000

def evaluate_recommendation(recommendation: dict[str, Any]) -> GuardrailDecision:
    run_id = str(recommendation.get("agent_run_id") or "")
    opportunity = recommendation.get("opportunity_type")
    action_type = f"{opportunity}_recommendation" if opportunity else None
    evidence = recommendation.get("evidence")
    product = recommendation.get("recommended_product")
    confidence = recommendation.get("confidence")
    impact = recommendation.get("estimated_revenue_impact")
    checks = [
        PolicyCheck(name="evidence", passed=isinstance(evidence, list) and bool(evidence), reason="Evidence is required."),
        PolicyCheck(name="opportunity_type", passed=opportunity in {"cross_sell", "upsell"}, reason="Only cross-sell and upsell are supported."),
        PolicyCheck(name="product", passed=isinstance(product, str) and bool(product.strip()), reason="A recommended product is required."),
        PolicyCheck(name="confidence", passed=confidence in MIN_CONFIDENCE, reason="Medium or high confidence is required."),
        PolicyCheck(name="action_type", passed=action_type in PERMITTED_ACTIONS, reason="Action type is not permitted."),
        PolicyCheck(name="estimated_value", passed=impact is None or (isinstance(impact, (int, float)) and impact <= MAX_ESTIMATED_VALUE), reason="Estimated value exceeds the permitted limit or is invalid."),
    ]
    failures = [check.reason for check in checks if not check.passed]
    decision = "allowed_for_approval" if not failures else ("insufficient_evidence" if not checks[0].passed else "blocked")
    return GuardrailDecision(recommendation_id=run_id, decision=decision, reasons=failures, policy_checks=checks, action_type=action_type, status="pending_approval" if decision == "allowed_for_approval" else "blocked")

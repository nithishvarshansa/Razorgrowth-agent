"""Read-only aggregation of already-stored agent_runs / approval_states /
commerce_actions / measurement_events data into a merchant-facing experiment
history. This module computes no new facts and performs no writes — every
field returned here already exists in the store; this only joins and
summarizes it deterministically. It never creates orders, calls Razorpay,
changes an approval, or records a measurement.
"""
from typing import Any

_DECISION_LABEL = {
    "approved": "Approved",
    "rejected": "Rejected",
    "pending_approval": "Pending merchant decision",
    "blocked": "Blocked by guardrail",
}

_EXECUTION_LABEL = {
    "executing": "Executing",
    "order_created": "Order created — awaiting payment",
    "payment_verified": "Executed",
    "failed": "Execution failed",
}

_OUTCOME_LABEL = {
    "recommendation_created": "Awaiting measurement",
    "guardrail_evaluated": "Awaiting measurement",
    "merchant_approved": "Awaiting measurement",
    "merchant_rejected": "Awaiting measurement",
    "checkout_started": "Awaiting measurement",
    "payment_attempted": "Awaiting measurement",
    "test_order_created": "Order created",
    "payment_verified": "Payment verified",
    "payment_failed": "Payment failed",
    "payment_cancelled": "Checkout cancelled",
}


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def build_experiment_history(
    runs: list[dict[str, Any]],
    approval_states: dict[str, dict[str, Any] | None],
    commerce_actions: dict[str, dict[str, Any] | None],
    measurements: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    approved = rejected = executed = payment_verified = failed = 0

    for run in runs:
        run_id = run.get("agent_run_id")
        approval = approval_states.get(run_id)
        commerce = commerce_actions.get(run_id)
        measurement = measurements.get(run_id)

        decision_status = approval.get("status") if approval else None
        execution_status = commerce.get("status") if commerce else None
        outcome_event = measurement.get("status") if measurement else None

        if decision_status == "approved":
            approved += 1
        elif decision_status == "rejected":
            rejected += 1

        if execution_status in ("order_created", "payment_verified"):
            executed += 1
        if execution_status == "payment_verified":
            payment_verified += 1
        if execution_status == "failed":
            failed += 1

        records.append({
            "agent_run_id": run_id,
            "opportunity_type": run.get("opportunity_type"),
            "recommended_product": run.get("recommended_product"),
            "customer_id": run.get("customer_id"),
            "confidence": run.get("confidence"),
            "priority": run.get("priority"),
            "status": run.get("status"),
            "expected_outcome": run.get("expected_outcome"),
            "started_at": run.get("started_at"),
            "decision_status": decision_status,
            "decision_label": _DECISION_LABEL.get(decision_status, "Not yet evaluated"),
            "execution_status": execution_status,
            "execution_label": _EXECUTION_LABEL.get(execution_status, "Not executed"),
            "outcome_event": outcome_event,
            "outcome_label": _OUTCOME_LABEL.get(outcome_event, "Awaiting measurement"),
        })

    total = len(records)
    summary = {
        "total_recommendations": total,
        "approved": approved,
        "rejected": rejected,
        "executed": executed,
        "payment_verified": payment_verified,
        "failed": failed,
        "approval_rate": round(approved / total, 4) if total else None,
        "execution_rate": round(executed / approved, 4) if approved else None,
        "payment_verification_rate": round(payment_verified / executed, 4) if executed else None,
    }

    learning: list[str] = []
    if approved:
        learning.append(f"{_plural(approved, 'recommendation')} {'has' if approved == 1 else 'have'} been approved.")
    if rejected:
        learning.append(f"The merchant rejected {_plural(rejected, 'recommendation')}.")
    if executed:
        learning.append(f"{_plural(executed, 'approved recommendation')} reached execution.")
    if payment_verified:
        learning.append(f"{_plural(payment_verified, 'executed action')} reached payment verification.")
    if failed:
        learning.append(f"{_plural(failed, 'execution attempt')} failed.")

    return {"history": records, "summary": summary, "learning": learning}

"""Deterministic, evidence-grounded growth hypotheses.

Given only the opportunity type the existing opportunity engine already
produces, this states what a Test Mode transaction could demonstrate —
always hedged, never a claim that the experiment already succeeded, and
never a fabricated number (revenue, conversion rate, or probability).
"""

_EXPECTED_OUTCOME = {
    "upsell": (
        "Customers showing repeated purchase behavior for this product may be receptive to a "
        "higher-value version of the same product. An additional successful Test Mode purchase "
        "would provide evidence that the recommended offer can generate another transaction."
    ),
    "cross_sell": (
        "Customers who purchase a related product from this merchant's assortment may also be "
        "receptive to this product. An additional successful Test Mode purchase would provide "
        "evidence that the recommended offer can generate another transaction."
    ),
}


def expected_outcome(opportunity_type: str | None) -> str | None:
    return _EXPECTED_OUTCOME.get(opportunity_type)

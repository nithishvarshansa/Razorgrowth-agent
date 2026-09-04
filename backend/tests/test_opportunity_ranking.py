from backend.services.opportunity_ranking import rank_opportunities


def _upsell(customer, product, evidence_count=1):
    return {
        "opportunity_type": "upsell",
        "customer_id": customer,
        "recommended_product": product,
        "reason": "test fixture reason",
        "evidence": [f"observed value {i}" for i in range(evidence_count)],
        "estimated_value": None,
        "confidence": "medium",
    }


def _cross_sell(customer, product):
    return {
        "opportunity_type": "cross_sell",
        "customer_id": customer,
        "recommended_product": product,
        "reason": "test fixture reason",
        "evidence": ["successful product-identified purchases"],
        "estimated_value": None,
        "confidence": "low",
    }


def test_empty_candidates_rank_to_empty_list():
    assert rank_opportunities([]) == []


def test_higher_confidence_ranks_above_lower_confidence_deterministically():
    low = _cross_sell("c1", "b")
    medium = _upsell("c2", "a")
    ranked = rank_opportunities([low, medium])
    assert [o["opportunity_type"] for o in ranked] == ["upsell", "cross_sell"]
    assert ranked[0]["priority"] == "MEDIUM"
    assert ranked[1]["priority"] == "LOW"


def test_ranking_is_deterministic_and_repeatable():
    candidates = [_cross_sell("c1", "b"), _upsell("c2", "a")]
    first = rank_opportunities(candidates)
    second = rank_opportunities(candidates)
    assert [(o["customer_id"], o["score"]) for o in first] == [(o["customer_id"], o["score"]) for o in second]


def test_equal_score_candidates_keep_original_order_as_tiebreak():
    a = _upsell("c1", "a")
    b = _upsell("c2", "b")
    ranked = rank_opportunities([a, b])
    assert [o["customer_id"] for o in ranked] == ["c1", "c2"]


def test_low_confidence_opportunity_is_marked_not_eligible_by_existing_guardrail_policy():
    ranked = rank_opportunities([_cross_sell("c1", "b")])
    assert ranked[0]["eligible"] is False
    assert ranked[0]["guardrail_decision"] == "blocked"
    assert "confidence" in " ".join(ranked[0]["guardrail_reasons"]).lower()


def test_medium_confidence_opportunity_is_eligible():
    ranked = rank_opportunities([_upsell("c1", "a")])
    assert ranked[0]["eligible"] is True
    assert ranked[0]["guardrail_decision"] == "allowed_for_approval"


def test_already_decided_opportunity_is_flagged_and_ranked_below_eligible_ones():
    decided = _upsell("c1", "a")
    fresh = _upsell("c2", "b")
    exclude = {("c1", "a", "upsell")}
    ranked = rank_opportunities([decided, fresh], exclude=exclude)
    assert ranked[0]["customer_id"] == "c2" and ranked[0]["already_decided"] is False
    assert ranked[1]["customer_id"] == "c1" and ranked[1]["already_decided"] is True
    assert ranked[1]["eligible"] is False

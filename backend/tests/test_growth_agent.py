from backend.models.analytics import NormalizedOrder, NormalizedPayment
from backend.services.agent_provider import DeterministicDevelopmentProvider, GrowthAgentProvider
from backend.services.growth_agent import GrowthAgentService
from backend.services.hypothesis import expected_outcome
from backend.services.opportunity_engine import analyze_opportunities


def _fixture_purchase(order_id, customer, product, amount):
    return NormalizedOrder(order_id, "paid", amount, "INR", customer, product, None, 1), NormalizedPayment(f"pay_{order_id}", order_id, "captured", amount, "INR", customer, 1, True, False)


def test_agent_run_returns_insufficient_evidence_for_empty_data():
    result = GrowthAgentService().run([], [])
    assert result.status == "insufficient_evidence"
    assert result.recommendation is None
    assert result.estimated_revenue_impact is None


def test_agent_recommends_supported_cross_sell_from_test_fixture():
    o1, p1 = _fixture_purchase("1", "c1", "a", 100)
    o2, p2 = _fixture_purchase("2", "c2", "a", 100)
    o3, p3 = _fixture_purchase("3", "c2", "b", 100)
    result = GrowthAgentService().run([o1, o2, o3], [p1, p2, p3])
    assert result.status == "recommended"
    assert result.opportunity_type == "cross_sell"
    assert result.mode == "deterministic_development"


def test_recommended_result_carries_the_matching_deterministic_hypothesis():
    o1, p1 = _fixture_purchase("1", "c1", "a", 100)
    o2, p2 = _fixture_purchase("2", "c1", "a", 200)
    result = GrowthAgentService().run([o1, o2], [p1, p2])
    assert result.status == "recommended"
    assert result.opportunity_type == "upsell"
    assert result.expected_outcome == expected_outcome("upsell")
    assert result.expected_outcome is not None


def test_insufficient_evidence_result_carries_no_hypothesis():
    result = GrowthAgentService().run([], [])
    assert result.status == "insufficient_evidence"
    assert result.expected_outcome is None


def test_provider_is_an_abstraction_and_rejects_invalid_opportunities():
    provider = DeterministicDevelopmentProvider()
    assert isinstance(provider, GrowthAgentProvider)
    assert provider.recommend({"opportunities": [{"opportunity_type": "upsell"}]}, {}) is None


def test_agent_never_exposes_financial_action_or_secret():
    result = GrowthAgentService().run([], [])
    payload = result.model_dump_json().lower()
    assert "secret" not in payload
    assert "execute" not in payload


def test_agent_excludes_already_decided_opportunities_and_learns_next_action():
    o1, p1 = _fixture_purchase("1", "c1", "a", 100)
    o2, p2 = _fixture_purchase("2", "c2", "a", 100)
    o3, p3 = _fixture_purchase("3", "c2", "b", 100)
    orders, payments = [o1, o2, o3], [p1, p2, p3]

    first = GrowthAgentService().run(orders, payments)
    assert first.status == "recommended"
    decided = {(first.customer_id, first.recommended_product, first.opportunity_type)}

    second = GrowthAgentService().run(orders, payments, exclude=decided)
    assert "Excluded 1 opportunity the merchant already decided on." in second.observed_facts
    if second.status == "recommended":
        assert (second.customer_id, second.recommended_product, second.opportunity_type) != next(iter(decided))
    else:
        assert "already been decided" in second.reasoning


def test_agent_ranks_multiple_opportunities_and_explains_the_selection():
    o1, p1 = _fixture_purchase("1", "c1", "a", 100)
    o2, p2 = _fixture_purchase("2", "c1", "a", 200)
    o3, p3 = _fixture_purchase("3", "c2", "b", 150)
    o4, p4 = _fixture_purchase("4", "c2", "b", 250)
    orders, payments = [o1, o2, o3, o4], [p1, p2, p3, p4]

    result = GrowthAgentService().run(orders, payments)
    assert result.status == "recommended"
    assert result.priority in ("HIGH", "MEDIUM", "LOW")
    assert len(result.ranked_opportunities) == 2
    assert "other opportunit" in result.reasoning
    assert result.customer_id == "c1" and result.recommended_product == "a"


def test_agent_reports_no_new_action_when_every_opportunity_is_decided():
    o1, p1 = _fixture_purchase("1", "c1", "a", 100)
    o2, p2 = _fixture_purchase("2", "c1", "a", 200)
    orders, payments = [o1, o2], [p1, p2]
    opportunities = analyze_opportunities(orders, payments)["opportunities"]
    decided = {(c["customer_id"], c["recommended_product"], c["opportunity_type"]) for c in opportunities}

    result = GrowthAgentService().run(orders, payments, exclude=decided)
    assert result.status == "insufficient_evidence"
    assert "already been decided" in result.reasoning

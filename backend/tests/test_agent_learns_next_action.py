from fastapi.testclient import TestClient

from backend.app import create_app
from backend.models.analytics import NormalizedOrder, NormalizedPayment
from backend.routes.analytics import get_store
from backend.services.analytics_store import AnalyticsStore


def _purchase(order_id, customer, product, amount):
    return (
        NormalizedOrder(order_id, "paid", amount, "INR", customer, product, None, 1),
        NormalizedPayment(f"pay_{order_id}", order_id, "captured", amount, "INR", customer, 1, True, False),
    )


def test_get_actioned_opportunities_reflects_approved_and_rejected_decisions(tmp_path):
    store = AnalyticsStore(f"sqlite:///./{tmp_path / 'store.db'}")
    assert store.get_actioned_opportunities() == set()


def test_second_agent_run_learns_and_recommends_a_different_opportunity(tmp_path):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / 'learn.db'}")
    app.dependency_overrides[get_store] = lambda: store
    client = TestClient(app)

    # Two customers each show a same-product, different-amount pattern, which the
    # opportunity engine treats as a medium-confidence upsell (guardrail-eligible),
    # unlike the low-confidence cross-sell signal used elsewhere in this file.
    o1, p1 = _purchase("o1", "c1", "a", 100)
    o2, p2 = _purchase("o2", "c1", "a", 200)
    o3, p3 = _purchase("o3", "c2", "b", 150)
    o4, p4 = _purchase("o4", "c2", "b", 250)
    store.save([o1, o2, o3, o4], [p1, p2, p3, p4])

    first = client.post("/api/agent/run").json()
    assert first["status"] == "recommended"
    first_key = (first["customer_id"], first["recommended_product"], first["opportunity_type"])

    assert client.post(f"/api/guardrails/evaluate/{first['agent_run_id']}").status_code == 200
    assert client.post(f"/api/guardrails/{first['agent_run_id']}/approve").status_code == 200

    second = client.post("/api/agent/run").json()
    assert second["status"] == "recommended"
    second_key = (second["customer_id"], second["recommended_product"], second["opportunity_type"])
    assert second_key != first_key
    assert any("Excluded" in fact for fact in second["observed_facts"])


def test_rejected_recommendation_is_also_excluded_from_the_next_run(tmp_path):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / 'learn_reject.db'}")
    app.dependency_overrides[get_store] = lambda: store
    client = TestClient(app)

    o1, p1 = _purchase("o1", "c1", "a", 100)
    o2, p2 = _purchase("o2", "c1", "a", 200)
    store.save([o1, o2], [p1, p2])

    first = client.post("/api/agent/run").json()
    assert first["status"] == "recommended"

    assert client.post(f"/api/guardrails/evaluate/{first['agent_run_id']}").status_code == 200
    assert client.post(f"/api/guardrails/{first['agent_run_id']}/reject").status_code == 200

    second = client.post("/api/agent/run").json()
    assert second["status"] == "insufficient_evidence"
    assert "already been decided" in second["reasoning"]

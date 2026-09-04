"""Failure & Recovery Center: proves the existing architecture already produces
a real, honest failed-execution state, blocks duplicate execution, preserves
the merchant decision/audit trail, and keeps a failed action excluded from
future ranking — with zero fabricated payments or invented Razorpay responses.
"""
import hashlib
import hmac

import httpx
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.models.analytics import NormalizedOrder, NormalizedPayment
from backend.routes.analytics import get_store
from backend.routes.razorpay import get_razorpay_service
from backend.services.analytics_store import AnalyticsStore
from backend.services.razorpay import RazorpayService


def _approved_demo_recommendation(client: TestClient) -> str:
    recommendation = client.post("/api/demo/recommendation")
    assert recommendation.status_code == 200
    run_id = recommendation.json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    approval = client.post(f"/api/guardrails/{run_id}/approve")
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"
    return run_id


def _client_with_razorpay(tmp_path, name, requester):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / name}")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="test_secret"), requester
    )
    return TestClient(app), store


def test_create_test_order_failure_is_recorded_without_fabricating_success(tmp_path):
    failing = lambda *a, **k: httpx.Response(502, json={"error": {"description": "upstream unavailable"}})
    client, store = _client_with_razorpay(tmp_path, "fail_create.db", failing)
    run_id = _approved_demo_recommendation(client)

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 502

    action = store.get_commerce_action(run_id)
    assert action["status"] == "failed"

    state = client.get(f"/api/measurement/{run_id}").json()
    event_types = [e["event_type"] for e in state["events"]]
    assert "payment_failed" in event_types
    assert "payment_verified" not in event_types

    # The merchant's approval decision and guardrail state are untouched by the failure.
    approval = store.load_approval_state(run_id)
    assert approval["status"] == "approved"


def test_duplicate_test_order_creation_is_blocked_after_failure(tmp_path):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"id": "order_test_1", "amount": 50000, "currency": "INR"})
        raise AssertionError("Razorpay should not be called again once a commerce action already exists")

    client, store = _client_with_razorpay(tmp_path, "duplicate.db", flaky)
    run_id = _approved_demo_recommendation(client)

    first = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert first.status_code == 200
    assert first.json()["razorpay_order_id"] == "order_test_1"

    second = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]

    # Exactly one commerce action/order was ever created for this recommendation.
    action = store.get_commerce_action(run_id)
    assert action["razorpay_order_id"] == "order_test_1"
    assert calls["n"] == 1


def test_payment_verification_failure_is_recorded_honestly(tmp_path):
    success = lambda *a, **k: httpx.Response(200, json={"id": "order_test_2", "amount": 50000, "currency": "INR"})
    client, store = _client_with_razorpay(tmp_path, "verify_fail.db", success)
    run_id = _approved_demo_recommendation(client)

    order = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert order.status_code == 200
    razorpay_order_id = order.json()["razorpay_order_id"]

    # A deliberately wrong signature — this exercises the existing verification
    # code path in a test, it does not change or weaken it.
    bad_signature = hmac.new(b"not_the_real_secret", f"{razorpay_order_id}|pay_fake".encode(), hashlib.sha256).hexdigest()
    verify = client.post(
        "/api/commerce/verify-payment",
        json={"razorpay_payment_id": "pay_fake", "razorpay_order_id": razorpay_order_id, "razorpay_signature": bad_signature},
    )
    assert verify.status_code == 400

    action = store.get_commerce_action(run_id)
    assert action["status"] == "failed"

    state = client.get(f"/api/measurement/{run_id}").json()
    event_types = [e["event_type"] for e in state["events"]]
    assert "payment_failed" in event_types
    assert "payment_verified" not in event_types


def test_failed_execution_recommendation_stays_excluded_from_next_run(tmp_path):
    failing = lambda *a, **k: httpx.Response(502, json={"error": {"description": "upstream unavailable"}})
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / 'exclude_after_failure.db'}")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="test_secret"), failing
    )
    client = TestClient(app)

    def purchase(order_id, customer, product, amount):
        return (
            NormalizedOrder(order_id, "paid", amount, "INR", customer, product, None, 1),
            NormalizedPayment(f"pay_{order_id}", order_id, "captured", amount, "INR", customer, 1, True, False),
        )

    o1, p1 = purchase("o1", "c1", "a", 100)
    o2, p2 = purchase("o2", "c1", "a", 200)
    o3, p3 = purchase("o3", "c2", "b", 150)
    o4, p4 = purchase("o4", "c2", "b", 250)
    store.save([o1, o2, o3, o4], [p1, p2, p3, p4])

    first = client.post("/api/agent/run").json()
    assert first["status"] == "recommended"
    first_key = (first["customer_id"], first["recommended_product"], first["opportunity_type"])

    assert client.post(f"/api/guardrails/evaluate/{first['agent_run_id']}").status_code == 200
    assert client.post(f"/api/guardrails/{first['agent_run_id']}/approve").status_code == 200

    # Execution fails — commerce_action becomes "failed"; the merchant's approval
    # decision (the input to decision memory) is untouched by this outcome. A real
    # (non-demo-prefixed) approved recommendation is permitted to reach Razorpay —
    # the mocked upstream failure is what actually blocks it here.
    failed_order = client.post(f"/api/commerce/{first['agent_run_id']}/create-test-order")
    assert failed_order.status_code == 502

    second = client.post("/api/agent/run").json()
    assert second["status"] == "recommended"
    second_key = (second["customer_id"], second["recommended_product"], second["opportunity_type"])
    assert second_key != first_key
    assert any("Excluded" in fact for fact in second["observed_facts"])

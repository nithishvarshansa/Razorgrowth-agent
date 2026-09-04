"""AI Growth Experiment: a real (non-demo-prefixed) recommendation from real
analytics data, carried through guardrail evaluation, merchant approval, the
existing TEST MODE commerce boundary, payment verification, measurement, and
closed-loop decision memory. No payment is ever mocked as succeeding without
the real signature-verification code path also being exercised; no revenue,
customer, or experiment-success claim is fabricated anywhere in this file.
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


def _purchase(order_id, customer, product, amount):
    return (
        NormalizedOrder(order_id, "paid", amount, "INR", customer, product, None, 1),
        NormalizedPayment(f"pay_{order_id}", order_id, "captured", amount, "INR", customer, 1, True, False),
    )


def _client(tmp_path, name, requester=None):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / name}")
    app.dependency_overrides[get_store] = lambda: store
    if requester is not None:
        app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
            Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="test_secret"), requester
        )
    return TestClient(app), store


def _seed_upsell_opportunity(store):
    # One customer, same product, two different amounts — the existing opportunity
    # engine's upsell pattern (medium confidence, guardrail-eligible).
    o1, p1 = _purchase("o1", "c1", "a", 100)
    o2, p2 = _purchase("o2", "c1", "a", 200)
    store.save([o1, o2], [p1, p2])


# ---------- safety ----------

def test_real_recommendation_never_exposes_razorpay_secrets(tmp_path):
    secret = "very-private-secret"
    client, store = _client(tmp_path, "safety_secret.db")
    _seed_upsell_opportunity(store)
    client.app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret=secret),
        lambda *a, **k: httpx.Response(200, json={"id": "order_x", "amount": 50000, "currency": "INR"}),
    )
    response = client.post("/api/agent/run")
    assert secret not in response.text
    assert "rzp_test_key" not in response.text


def test_real_recommendation_does_not_expose_unauthorized_execution_instructions(tmp_path):
    client, store = _client(tmp_path, "safety_execute.db")
    _seed_upsell_opportunity(store)
    response = client.post("/api/agent/run")
    payload = response.text.lower()
    assert "execute" not in payload
    for claim in ("proven", "guaranteed", "will buy", "validated", "will increase"):
        assert claim not in payload


# ---------- approval gating for a real (non-demo) recommendation ----------

def test_pending_real_recommendation_cannot_execute(tmp_path):
    client, store = _client(tmp_path, "gate_pending.db")
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 409
    assert store.get_commerce_action(run_id) is None


def test_rejected_real_recommendation_cannot_execute(tmp_path):
    client, store = _client(tmp_path, "gate_rejected.db")
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/reject").status_code == 200

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 409
    assert store.get_commerce_action(run_id) is None


def test_approved_real_recommendation_reaches_the_existing_test_mode_commerce_boundary(tmp_path):
    success = lambda *a, **k: httpx.Response(200, json={"id": "order_real_1", "amount": 50000, "currency": "INR"})
    client, store = _client(tmp_path, "gate_approved.db", success)
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 200
    body = response.json()
    assert body["razorpay_order_id"] == "order_real_1"
    assert body["environment"] == "TEST MODE"
    assert body["demo_data"] is False  # honestly labeled: this is a real detected opportunity, not fixture data


def test_duplicate_execution_remains_blocked_for_a_real_recommendation(tmp_path):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"id": "order_real_dup", "amount": 50000, "currency": "INR"})
        raise AssertionError("Razorpay should not be called again once a commerce action already exists")

    client, store = _client(tmp_path, "gate_duplicate.db", flaky)
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200

    first = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert first.status_code == 200
    second = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]
    assert calls["n"] == 1


def test_existing_demo_flow_still_reaches_test_mode_commerce(tmp_path):
    success = lambda *a, **k: httpx.Response(200, json={"id": "order_demo_1", "amount": 50000, "currency": "INR"})
    client, store = _client(tmp_path, "demo_still_works.db", success)

    run_id = client.post("/api/demo/recommendation").json()["agent_run_id"]
    assert run_id.startswith("demo-")
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 200
    assert response.json()["demo_data"] is True


# ---------- closed loop: real opportunity -> hypothesis -> guardrail -> approval
# -> mocked TEST MODE order -> mocked verified payment -> measurement -> excluded ----------

def test_full_closed_loop_from_real_opportunity_to_excluded_next_run(tmp_path):
    order_response = {"id": "order_loop_1", "amount": 50000, "currency": "INR"}
    success = lambda *a, **k: httpx.Response(200, json=order_response)
    client, store = _client(tmp_path, "closed_loop.db", success)
    _seed_upsell_opportunity(store)

    # 1-3: detect + rank + select a real opportunity
    first = client.post("/api/agent/run").json()
    assert first["status"] == "recommended"
    assert first["opportunity_type"] == "upsell"

    # 4: hypothesis exists and is evidence-grounded (no fabricated numbers/success claim)
    assert first["expected_outcome"]
    assert "higher-value" in first["expected_outcome"]

    # 5: guardrail evaluation
    guardrail = client.post(f"/api/guardrails/evaluate/{first['agent_run_id']}")
    assert guardrail.status_code == 200
    assert guardrail.json()["decision"] == "allowed_for_approval"

    # 6: merchant approval
    approval = client.post(f"/api/guardrails/{first['agent_run_id']}/approve")
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"

    # 7: TEST MODE order creation (mocked Razorpay, real code path)
    order = client.post(f"/api/commerce/{first['agent_run_id']}/create-test-order")
    assert order.status_code == 200
    razorpay_order_id = order.json()["razorpay_order_id"]
    assert razorpay_order_id == "order_loop_1"

    # 8-9: real signature verification code path with a genuinely valid signature,
    # and the resulting payment_verified measurement event recorded.
    key_secret = "test_secret"
    client.app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret=key_secret), success
    )
    payment_id = "pay_loop_1"
    signature = hmac.new(key_secret.encode(), f"{razorpay_order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    verify = client.post(
        "/api/commerce/verify-payment",
        json={"razorpay_payment_id": payment_id, "razorpay_order_id": razorpay_order_id, "razorpay_signature": signature},
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "payment_verified"

    measurement = client.get(f"/api/measurement/{first['agent_run_id']}").json()
    event_types = [e["event_type"] for e in measurement["events"]]
    assert "payment_verified" in event_types
    assert "payment_failed" not in event_types

    # 10-11: run the Growth Agent again — the already-actioned opportunity must be excluded.
    second = client.post("/api/agent/run").json()
    first_key = (first["customer_id"], first["recommended_product"], first["opportunity_type"])
    if second["status"] == "recommended":
        second_key = (second["customer_id"], second["recommended_product"], second["opportunity_type"])
        assert second_key != first_key
    else:
        assert second["status"] == "insufficient_evidence"
    assert any("excluded" in fact.lower() for fact in second["observed_facts"])


# ---------- failure paths for a real recommendation ----------

def test_mocked_razorpay_failure_for_a_real_recommendation_is_recorded_honestly(tmp_path):
    failing = lambda *a, **k: httpx.Response(502, json={"error": {"description": "upstream unavailable"}})
    client, store = _client(tmp_path, "real_fail_create.db", failing)
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200

    response = client.post(f"/api/commerce/{run_id}/create-test-order")
    assert response.status_code == 502
    action = store.get_commerce_action(run_id)
    assert action["status"] == "failed"
    events = [e["event_type"] for e in client.get(f"/api/measurement/{run_id}").json()["events"]]
    assert "payment_failed" in events
    assert "payment_verified" not in events
    # The approval decision itself is not touched by the execution failure.
    assert store.load_approval_state(run_id)["status"] == "approved"


def test_payment_verification_failure_for_a_real_recommendation_is_recorded_honestly(tmp_path):
    success = lambda *a, **k: httpx.Response(200, json={"id": "order_real_verify_fail", "amount": 50000, "currency": "INR"})
    client, store = _client(tmp_path, "real_verify_fail.db", success)
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200
    order = client.post(f"/api/commerce/{run_id}/create-test-order")
    razorpay_order_id = order.json()["razorpay_order_id"]

    bad_signature = hmac.new(b"not_the_real_secret", f"{razorpay_order_id}|pay_fake".encode(), hashlib.sha256).hexdigest()
    verify = client.post(
        "/api/commerce/verify-payment",
        json={"razorpay_payment_id": "pay_fake", "razorpay_order_id": razorpay_order_id, "razorpay_signature": bad_signature},
    )
    assert verify.status_code == 400
    assert store.get_commerce_action(run_id)["status"] == "failed"
    events = [e["event_type"] for e in client.get(f"/api/measurement/{run_id}").json()["events"]]
    assert "payment_failed" in events
    assert "payment_verified" not in events


def test_merchant_rejection_creates_no_order_and_no_payment(tmp_path):
    def unexpected(*a, **k):
        raise AssertionError("Razorpay must never be called for a rejected recommendation")

    client, store = _client(tmp_path, "real_rejected_no_order.db", unexpected)
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/reject").status_code == 200

    assert client.post(f"/api/commerce/{run_id}/create-test-order").status_code == 409
    assert store.get_commerce_action(run_id) is None
    events = [e["event_type"] for e in client.get(f"/api/measurement/{run_id}").json()["events"]]
    assert "payment_verified" not in events
    assert "test_order_created" not in events


def test_checkout_cancellation_event_is_supported_without_claiming_success(tmp_path):
    # Checkout cancellation happens client-side (the Razorpay Checkout modal is
    # dismissed before any payment attempt reaches the backend at all), so it is
    # recorded via the existing generic measurement endpoint — this proves that
    # path stays available and honest for a real (non-demo) recommendation too.
    client, store = _client(tmp_path, "real_cancelled.db")
    _seed_upsell_opportunity(store)
    run_id = client.post("/api/agent/run").json()["agent_run_id"]
    assert client.post(f"/api/guardrails/evaluate/{run_id}").status_code == 200
    assert client.post(f"/api/guardrails/{run_id}/approve").status_code == 200

    response = client.post(
        f"/api/measurement/{run_id}/event",
        json={"event_type": "payment_cancelled", "metadata": {"reason": "Test checkout was cancelled."}},
    )
    assert response.status_code == 200

    events = [e["event_type"] for e in client.get(f"/api/measurement/{run_id}").json()["events"]]
    assert "payment_cancelled" in events
    assert "payment_verified" not in events

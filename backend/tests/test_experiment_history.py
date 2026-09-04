"""Experiment History & Learning: a read-only join over already-stored
agent_runs/approval_states/commerce_actions/measurement_events. No test here
creates an order, calls Razorpay, or mutates approval/measurement state beyond
what the existing, separately-tested flows already do.
"""
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.routes.analytics import get_store
from backend.services.analytics_store import AnalyticsStore
from backend.services.experiment_history import build_experiment_history


def _client(tmp_path, name):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / name}")
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app), store


# ---------- pure aggregation function ----------

def test_empty_history_has_zero_counts_and_no_rates():
    result = build_experiment_history([], {}, {}, {})
    assert result["history"] == []
    assert result["summary"] == {
        "total_recommendations": 0, "approved": 0, "rejected": 0, "executed": 0,
        "payment_verified": 0, "failed": 0,
        "approval_rate": None, "execution_rate": None, "payment_verification_rate": None,
    }
    assert result["learning"] == []


def test_single_recommendation_with_no_decision_yet():
    run = {"agent_run_id": "r1", "opportunity_type": "upsell", "recommended_product": "a", "status": "recommended", "expected_outcome": "hedged hypothesis text"}
    result = build_experiment_history([run], {"r1": None}, {"r1": None}, {"r1": {"status": "recommendation_created"}})
    record = result["history"][0]
    assert record["decision_label"] == "Not yet evaluated"
    assert record["execution_label"] == "Not executed"
    assert record["outcome_label"] == "Awaiting measurement"
    assert record["expected_outcome"] == "hedged hypothesis text"
    assert result["summary"]["total_recommendations"] == 1
    assert result["summary"]["approval_rate"] == 0.0
    assert result["learning"] == []  # no decision, no execution -> nothing to report yet


def test_rejected_recommendation_is_counted_and_labeled():
    run = {"agent_run_id": "r1", "opportunity_type": "cross_sell", "recommended_product": "a"}
    result = build_experiment_history([run], {"r1": {"status": "rejected"}}, {"r1": None}, {"r1": {"status": "merchant_rejected"}})
    assert result["summary"]["rejected"] == 1
    assert result["history"][0]["decision_label"] == "Rejected"
    assert result["history"][0]["execution_label"] == "Not executed"
    assert "The merchant rejected 1 recommendation." in result["learning"]


def test_full_happy_path_approved_executed_and_payment_verified():
    run = {"agent_run_id": "r1", "opportunity_type": "upsell", "recommended_product": "a"}
    result = build_experiment_history(
        [run],
        {"r1": {"status": "approved"}},
        {"r1": {"status": "payment_verified"}},
        {"r1": {"status": "payment_verified"}},
    )
    summary = result["summary"]
    assert summary["approved"] == 1 and summary["executed"] == 1 and summary["payment_verified"] == 1
    assert summary["approval_rate"] == 1.0
    assert summary["execution_rate"] == 1.0
    assert summary["payment_verification_rate"] == 1.0
    record = result["history"][0]
    assert record["execution_label"] == "Executed"
    assert record["outcome_label"] == "Payment verified"
    assert "1 recommendation has been approved." in result["learning"]
    assert "1 approved recommendation reached execution." in result["learning"]
    assert "1 executed action reached payment verification." in result["learning"]


def test_failed_execution_is_counted_and_does_not_count_as_executed_toward_payment_verified():
    run = {"agent_run_id": "r1", "opportunity_type": "upsell", "recommended_product": "a"}
    result = build_experiment_history(
        [run], {"r1": {"status": "approved"}}, {"r1": {"status": "failed"}}, {"r1": {"status": "payment_failed"}},
    )
    summary = result["summary"]
    assert summary["failed"] == 1
    assert summary["executed"] == 0  # a failed order-creation/verification never counted as a real execution
    assert summary["payment_verified"] == 0
    assert result["history"][0]["execution_label"] == "Execution failed"
    assert result["history"][0]["outcome_label"] == "Payment failed"
    assert "1 execution attempt failed." in result["learning"]


def test_mixed_records_aggregate_correctly():
    runs = [{"agent_run_id": f"r{i}", "opportunity_type": "upsell", "recommended_product": "a"} for i in range(4)]
    approvals = {"r0": {"status": "approved"}, "r1": {"status": "approved"}, "r2": {"status": "rejected"}, "r3": None}
    commerce = {"r0": {"status": "payment_verified"}, "r1": {"status": "order_created"}, "r2": None, "r3": None}
    measurements = {rid: {"status": None} for rid in ["r0", "r1", "r2", "r3"]}
    result = build_experiment_history(runs, approvals, commerce, measurements)
    summary = result["summary"]
    assert summary["total_recommendations"] == 4
    assert summary["approved"] == 2
    assert summary["rejected"] == 1
    assert summary["executed"] == 2  # order_created counts as executed even without payment_verified yet
    assert summary["payment_verified"] == 1
    assert summary["approval_rate"] == 0.5
    assert summary["execution_rate"] == 1.0  # 2 executed / 2 approved


# ---------- route-level: real store, no fabricated data, no side effects ----------

def test_history_route_returns_empty_state_with_no_agent_runs(tmp_path):
    client, _ = _client(tmp_path, "empty_history.db")
    response = client.get("/api/experiments/history")
    assert response.status_code == 200
    body = response.json()
    assert body["history"] == []
    assert body["summary"]["total_recommendations"] == 0


def test_history_route_reflects_a_real_demo_lifecycle_without_creating_anything(tmp_path):
    client, store = _client(tmp_path, "real_history.db")

    recommendation = client.post("/api/demo/recommendation")
    run_id = recommendation.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")
    client.post(f"/api/guardrails/{run_id}/approve")

    response = client.get("/api/experiments/history")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_recommendations"] == 1
    assert body["summary"]["approved"] == 1
    record = next(r for r in body["history"] if r["agent_run_id"] == run_id)
    assert record["decision_label"] == "Approved"
    assert record["execution_label"] == "Not executed"

    # The history endpoint itself created no commerce action and recorded no
    # new measurement event as a side effect of simply being read.
    assert store.get_commerce_action(run_id) is None
    events_before = len(store.get_measurement_events(run_id))
    client.get("/api/experiments/history")
    assert len(store.get_measurement_events(run_id)) == events_before


def test_history_route_never_exposes_razorpay_secrets(tmp_path):
    client, store = _client(tmp_path, "history_secrets.db")
    client.post("/api/demo/recommendation")
    response = client.get("/api/experiments/history")
    assert "key_secret" not in response.text
    assert "razorpay_key_secret" not in response.text

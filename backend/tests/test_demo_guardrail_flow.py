import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.routes.analytics import get_store
from backend.services.analytics_store import DEMO_REUSE_WINDOW, AnalyticsStore


def test_demo_recommendation_can_be_evaluated_by_guardrails(tmp_path):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: AnalyticsStore(f"sqlite:///./{tmp_path / 'demo.db'}")
    client = TestClient(app)
    recommendation = client.post("/api/demo/recommendation")
    assert recommendation.status_code == 200
    run_id = recommendation.json()["agent_run_id"]
    evaluation = client.post(f"/api/guardrails/evaluate/{run_id}")
    assert evaluation.status_code != 404
    assert evaluation.status_code == 200


def _client(tmp_path, name):
    app = create_app()
    store = AnalyticsStore(f"sqlite:///./{tmp_path / name}")
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app), store


def test_stale_unresolved_demo_run_does_not_replace_a_new_demo_run(tmp_path):
    """A demo run abandoned in an earlier session is history, not the experiment
    currently in progress — clicking Run Growth Demo must start a fresh one."""
    client, store = _client(tmp_path, "demo_stale.db")

    stale = client.post("/api/demo/recommendation")
    stale_id = stale.json()["agent_run_id"]

    # Age the unresolved run past the reuse window, exactly as an abandoned run
    # from an earlier session would be. No row is added, removed, or faked.
    old = (datetime.now(UTC) - DEMO_REUSE_WINDOW - timedelta(minutes=5)).isoformat()
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE agent_runs SET started_at=? WHERE id=?", (old, stale_id))

    fresh = client.post("/api/demo/recommendation")

    assert fresh.json()["agent_run_id"] != stale_id
    assert len(store.load_agent_runs()) == 2
    # The stale run is still in history — nothing was deleted to achieve this.
    assert store.find_agent_run(stale_id) is not None


def test_second_demo_run_reuses_the_first_while_unresolved(tmp_path):
    client, store = _client(tmp_path, "demo_dedupe.db")

    first = client.post("/api/demo/recommendation")
    second = client.post("/api/demo/recommendation")

    assert first.json()["agent_run_id"] == second.json()["agent_run_id"]
    assert len(store.load_agent_runs()) == 1


def test_demo_run_is_reused_even_after_guardrail_evaluation_while_still_pending(tmp_path):
    client, store = _client(tmp_path, "demo_dedupe_pending.db")

    first = client.post("/api/demo/recommendation")
    run_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")

    second = client.post("/api/demo/recommendation")

    assert second.json()["agent_run_id"] == run_id
    assert len(store.load_agent_runs()) == 1


def test_a_new_demo_run_is_created_once_the_previous_one_is_approved(tmp_path):
    client, store = _client(tmp_path, "demo_dedupe_approved.db")

    first = client.post("/api/demo/recommendation")
    first_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{first_id}")
    client.post(f"/api/guardrails/{first_id}/approve")

    second = client.post("/api/demo/recommendation")

    assert second.json()["agent_run_id"] != first_id
    assert len(store.load_agent_runs()) == 2


def test_a_new_demo_run_is_created_once_the_previous_one_is_rejected(tmp_path):
    client, store = _client(tmp_path, "demo_dedupe_rejected.db")

    first = client.post("/api/demo/recommendation")
    first_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{first_id}")
    client.post(f"/api/guardrails/{first_id}/reject")

    second = client.post("/api/demo/recommendation")

    assert second.json()["agent_run_id"] != first_id
    assert len(store.load_agent_runs()) == 2


def test_approved_executed_and_payment_verified_demo_run_remains_in_history(tmp_path):
    client, store = _client(tmp_path, "demo_history_approved.db")

    first = client.post("/api/demo/recommendation")
    run_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")
    client.post(f"/api/guardrails/{run_id}/approve")
    store.create_commerce_action(run_id, "action-1", {"razorpay_order_id": "order_1"})
    store.update_commerce_action(run_id, "payment_verified", "order_1", {"razorpay_order_id": "order_1"})

    history = client.get("/api/experiments/history").json()
    record = next(r for r in history["history"] if r["agent_run_id"] == run_id)
    assert record["decision_label"] == "Approved"
    assert record["outcome_label"] == "Payment verified"


def test_rejected_demo_run_remains_in_history(tmp_path):
    client, store = _client(tmp_path, "demo_history_rejected.db")

    first = client.post("/api/demo/recommendation")
    run_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")
    client.post(f"/api/guardrails/{run_id}/reject")

    history = client.get("/api/experiments/history").json()
    record = next(r for r in history["history"] if r["agent_run_id"] == run_id)
    assert record["decision_label"] == "Rejected"


def test_failed_demo_run_remains_in_history(tmp_path):
    client, store = _client(tmp_path, "demo_history_failed.db")

    first = client.post("/api/demo/recommendation")
    run_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")
    client.post(f"/api/guardrails/{run_id}/approve")
    store.create_commerce_action(run_id, "action-1", {"razorpay_order_id": "order_1"})
    store.update_commerce_action(run_id, "failed", "order_1", {"razorpay_order_id": "order_1"})

    history = client.get("/api/experiments/history").json()
    record = next(r for r in history["history"] if r["agent_run_id"] == run_id)
    assert record["execution_label"] == "Execution failed"


def test_closed_loop_exclusion_still_treats_a_decided_demo_run_as_actioned(tmp_path):
    client, store = _client(tmp_path, "demo_closed_loop.db")

    first = client.post("/api/demo/recommendation")
    run_id = first.json()["agent_run_id"]
    client.post(f"/api/guardrails/evaluate/{run_id}")
    client.post(f"/api/guardrails/{run_id}/approve")

    run = store.find_agent_run(run_id)
    key = (run["customer_id"], run["recommended_product"], run["opportunity_type"])
    assert key in store.get_actioned_opportunities()

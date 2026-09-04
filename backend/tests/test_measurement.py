from fastapi.testclient import TestClient

from backend.app import create_app
from backend.routes.analytics import get_store
from backend.services.analytics_store import AnalyticsStore


def test_measurement_tracks_real_lifecycle_without_fabricated_payment(tmp_path):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: AnalyticsStore(f"sqlite:///./{tmp_path / 'measurement.db'}")
    client = TestClient(app)

    recommendation = client.post("/api/demo/recommendation")
    assert recommendation.status_code == 200
    recommendation_id = recommendation.json()["agent_run_id"]

    evaluation = client.post(f"/api/guardrails/evaluate/{recommendation_id}")
    assert evaluation.status_code == 200
    assert evaluation.json()["status"] == "pending_approval"

    approval = client.post(f"/api/guardrails/{recommendation_id}/approve")
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"

    checkout_started = client.post(
        f"/api/measurement/{recommendation_id}/event",
        json={"event_type": "checkout_started", "metadata": {"mode": "demo/test"}},
    )
    assert checkout_started.status_code == 200

    state = client.get(f"/api/measurement/{recommendation_id}")
    assert state.status_code == 200

    payload = state.json()
    event_types = [event["event_type"] for event in payload["events"]]
    assert "recommendation_created" in event_types
    assert "guardrail_evaluated" in event_types
    assert "merchant_approved" in event_types
    assert "checkout_started" in event_types
    assert "payment_verified" not in event_types
    assert payload["status"] == "checkout_started"


def test_measurement_rejects_invalid_event_type():
    app = create_app()
    app.dependency_overrides[get_store] = lambda: AnalyticsStore("sqlite:///./test_measurement_invalid.db")
    client = TestClient(app)

    recommendation = client.post("/api/demo/recommendation")
    assert recommendation.status_code == 200
    recommendation_id = recommendation.json()["agent_run_id"]

    invalid = client.post(
        f"/api/measurement/{recommendation_id}/event",
        json={"event_type": "made_up_event", "metadata": {}},
    )
    assert invalid.status_code == 400

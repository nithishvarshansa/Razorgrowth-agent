from fastapi import APIRouter, Depends, HTTPException

from ..routes.analytics import get_store
from ..services.analytics_store import AnalyticsStore

router = APIRouter(prefix="/api/measurement", tags=["measurement"])


@router.get("/{recommendation_id}")
def get_measurement_state(recommendation_id: str, store: AnalyticsStore = Depends(get_store)):
    state = store.get_measurement_state(recommendation_id)
    if not state["events"]:
        raise HTTPException(404, "Measurement state not found.")
    return state


@router.post("/{recommendation_id}/event")
def add_measurement_event(recommendation_id: str, body: dict, store: AnalyticsStore = Depends(get_store)):
    event_type = body.get("event_type")
    if not event_type or event_type not in store.VALID_MEASUREMENT_EVENTS:
        raise HTTPException(400, "Unsupported measurement event type.")
    metadata = body.get("metadata") or {}
    mode = str(metadata.get("mode") or "demo/test")
    return store.record_measurement_event(recommendation_id, event_type, metadata, mode=mode)

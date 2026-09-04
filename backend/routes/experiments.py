from fastapi import APIRouter, Depends

from ..routes.analytics import get_store
from ..services.analytics_store import AnalyticsStore
from ..services.experiment_history import build_experiment_history

router = APIRouter(prefix="/api/experiments", tags=["experiment-history"])


@router.get("/history")
def get_experiment_history(store: AnalyticsStore = Depends(get_store)) -> dict:
    """Read-only history/learning digest built from already-stored agent_runs,
    approval_states, commerce_actions, and measurement_events. Creates nothing,
    calls no external service, and mutates no state.
    """
    runs = store.load_agent_runs()
    run_ids = [run.get("agent_run_id") for run in runs if run.get("agent_run_id")]
    approval_states = {run_id: store.load_approval_state(run_id) for run_id in run_ids}
    commerce_actions = {run_id: store.get_commerce_action(run_id) for run_id in run_ids}
    measurements = {run_id: store.get_measurement_state(run_id) for run_id in run_ids}
    return build_experiment_history(runs, approval_states, commerce_actions, measurements)

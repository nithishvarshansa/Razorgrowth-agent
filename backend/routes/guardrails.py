from fastapi import APIRouter, Depends, HTTPException
from ..models.guardrails import GuardrailDecision
from ..routes.analytics import get_store
from ..services.analytics_store import AnalyticsStore
from ..services.guardrails import evaluate_recommendation

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])

@router.post("/evaluate/{agent_run_id}", response_model=GuardrailDecision)
def evaluate(agent_run_id: str, store: AnalyticsStore = Depends(get_store)):
    run = store.find_agent_run(agent_run_id)
    if not run: raise HTTPException(404, "Agent run not found.")
    decision = evaluate_recommendation(run)
    store.save_approval_state(decision, "guardrail_evaluated", "; ".join(decision.reasons) or None)
    return decision

@router.get("/{recommendation_id}", response_model=GuardrailDecision)
def get_status(recommendation_id: str, store: AnalyticsStore = Depends(get_store)):
    result = store.load_approval_state(recommendation_id)
    if not result: raise HTTPException(404, "Guardrail evaluation not found.")
    return result

def _set_status(recommendation_id: str, status: str, store: AnalyticsStore):
    saved = store.load_approval_state(recommendation_id)
    if not saved: raise HTTPException(404, "Guardrail evaluation not found.")
    if saved["status"] != "pending_approval": raise HTTPException(409, "Only pending recommendations can be decided.")
    saved["status"] = status
    result = GuardrailDecision(**saved)
    store.save_approval_state(result, f"merchant_{status}", f"Merchant {status} recommendation; no action executed.")
    return result

@router.post("/{recommendation_id}/approve", response_model=GuardrailDecision)
def approve(recommendation_id: str, store: AnalyticsStore = Depends(get_store)): return _set_status(recommendation_id, "approved", store)

@router.post("/{recommendation_id}/reject", response_model=GuardrailDecision)
def reject(recommendation_id: str, store: AnalyticsStore = Depends(get_store)): return _set_status(recommendation_id, "rejected", store)

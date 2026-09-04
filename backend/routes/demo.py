from fastapi import APIRouter, Depends
from ..models.agent import AgentRecommendation
from ..routes.analytics import get_store
from ..services.analytics_store import AnalyticsStore
from ..services.demo_fixture import demo_recommendation

router=APIRouter(prefix="/api/demo",tags=["demo-test-data"])
@router.post("/recommendation",response_model=AgentRecommendation)
def create_demo_recommendation(store: AnalyticsStore=Depends(get_store)):
    # Reuse an already-unresolved demo run instead of minting another one, so
    # repeated clicks while the merchant hasn't decided yet don't clutter
    # Experiment History with identical pending entries.
    existing = store.find_unresolved_demo_run()
    if existing is not None:
        return AgentRecommendation(**existing)
    result=demo_recommendation(); store.save_agent_run(result); return result

from fastapi import APIRouter, Depends
from typing import Any

from ..models.agent import AgentRecommendation
from ..routes.analytics import get_store
from ..services.analytics_store import AnalyticsStore
from ..services.growth_agent import GrowthAgentService

router = APIRouter(prefix="/api/agent", tags=["growth-agent"])


@router.post("/run", response_model=AgentRecommendation)
def run_growth_agent(store: AnalyticsStore = Depends(get_store)) -> AgentRecommendation:
    """Observe stored data, recommend only when evidence exists, then stop.

    Learns from past merchant decisions by excluding already-approved or
    already-rejected opportunities, so a repeat run surfaces the next action.
    """
    orders, payments = store.load()
    exclude = store.get_actioned_opportunities()
    result = GrowthAgentService().run(orders, payments, exclude=exclude)
    store.save_agent_run(result)
    return result


@router.get("/runs")
def get_agent_runs(store: AnalyticsStore = Depends(get_store)) -> dict[str, list[dict[str, Any]]]:
    return {"runs": store.load_agent_runs()}

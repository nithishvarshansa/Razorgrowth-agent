from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRecommendation(BaseModel):
    agent_run_id: str
    status: Literal["recommended", "insufficient_evidence"]
    mode: Literal["deterministic_development"]
    started_at: datetime
    ended_at: datetime
    opportunity_type: Literal["cross_sell", "upsell"] | None = None
    customer_id: str | None = None
    recommended_product: str | None = None
    observed_facts: list[str] = Field(default_factory=list)
    inferred_insight: str | None = None
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    confidence: str | None = None
    recommendation: str | None = None
    estimated_revenue_impact: None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None = None
    ranked_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    expected_outcome: str | None = None

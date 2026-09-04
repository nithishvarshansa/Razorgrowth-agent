"""Isolated hackathon demo fixture. Never included in Razorpay analytics."""
from datetime import UTC, datetime
from uuid import uuid4
from ..models.agent import AgentRecommendation
from .hypothesis import expected_outcome

DEMO_AMOUNT = 50000
DEMO_CURRENCY = "INR"

def demo_recommendation() -> AgentRecommendation:
    now = datetime.now(UTC)
    return AgentRecommendation(agent_run_id=f"demo-{uuid4()}", status="recommended", mode="deterministic_development", started_at=now, ended_at=now, opportunity_type="cross_sell", customer_id="demo_customer", recommended_product="demo_complementary_product", observed_facts=["DEMO / TEST DATA: isolated fixture"], inferred_insight="DEMO / TEST DATA: fixture purchase relationship.", reasoning="DEMO / TEST DATA only; not merchant analytics.", evidence=["DEMO / TEST DATA fixture evidence"], confidence="medium", recommendation="Review this DEMO / TEST DATA cross-sell before creating a Test Mode checkout.", expected_outcome=expected_outcome("cross_sell"))

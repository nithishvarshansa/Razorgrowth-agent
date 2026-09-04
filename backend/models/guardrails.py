from typing import Literal
from pydantic import BaseModel, Field

class PolicyCheck(BaseModel):
    name: str
    passed: bool
    reason: str

class GuardrailDecision(BaseModel):
    recommendation_id: str
    decision: Literal["allowed_for_approval", "blocked", "insufficient_evidence"]
    reasons: list[str] = Field(default_factory=list)
    policy_checks: list[PolicyCheck]
    requires_merchant_approval: bool = True
    action_type: str | None = None
    status: Literal["proposed", "blocked", "pending_approval", "approved", "rejected"]

from pydantic import BaseModel


class CommerceAction(BaseModel):
    action_id: str
    recommendation_id: str
    status: str
    environment: str = "TEST MODE"
    demo_data: bool = True
    razorpay_order_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    key_id: str | None = None

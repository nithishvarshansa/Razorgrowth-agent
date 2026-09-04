from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from ..routes.analytics import get_store
from ..routes.razorpay import get_razorpay_service
from ..services.analytics_store import AnalyticsStore
from ..services.demo_fixture import DEMO_AMOUNT, DEMO_CURRENCY
from ..services.razorpay import RazorpayService, RazorpayServiceError
from ..models.commerce import CommerceAction
from pydantic import BaseModel
router=APIRouter(prefix="/api/commerce",tags=["test-mode-commerce"])
@router.post("/{recommendation_id}/create-test-order",response_model=CommerceAction)
def create_test_order(recommendation_id:str,store:AnalyticsStore=Depends(get_store),razorpay:RazorpayService=Depends(get_razorpay_service)):
    state=store.load_approval_state(recommendation_id)
    if not state or state["status"]!="approved": raise HTTPException(409,"Merchant approval is required before a Test Mode order can be created.")
    run=store.find_agent_run(recommendation_id)
    if not run: raise HTTPException(409,"No recommendation was found for this id.")
    is_demo=str(recommendation_id).startswith("demo-")
    action_id=str(uuid4())
    pending={"action_id":action_id,"recommendation_id":recommendation_id,"environment":"TEST MODE","demo_data":is_demo,"amount":DEMO_AMOUNT,"currency":DEMO_CURRENCY}
    try: store.create_commerce_action(recommendation_id,action_id,pending)
    except Exception: raise HTTPException(409,"A Test Mode order action already exists for this recommendation.")
    source_note="DEMO / TEST DATA" if is_demo else "AI Growth Experiment — TEST MODE"
    try: result=razorpay.create_test_order(DEMO_AMOUNT,DEMO_CURRENCY,f"{'demo' if is_demo else 'exp'}-{action_id[:18]}",{"source":source_note,"recommendation_id":recommendation_id})
    except RazorpayServiceError as exc:
        store.update_commerce_action(recommendation_id,"failed",None,pending)
        raise HTTPException(exc.status_code,exc.message)
    payload={**pending,"razorpay_order_id":result.get("id"),"amount":result.get("amount"),"currency":result.get("currency"),"key_id":razorpay._settings.razorpay_key_id}
    store.update_commerce_action(recommendation_id,"order_created",result.get("id"),payload)
    return CommerceAction(**store.get_commerce_action(recommendation_id))

class PaymentVerification(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

@router.post("/verify-payment")
def verify_payment(body: PaymentVerification, store: AnalyticsStore=Depends(get_store), razorpay:RazorpayService=Depends(get_razorpay_service)):
    from ..services.payment_verification import verify_payment_signature
    action=store.find_commerce_action_by_order(body.razorpay_order_id)
    if not action or action["status"] != "order_created": raise HTTPException(400,"Unknown or ineligible Test Mode order.")
    if not verify_payment_signature(action["razorpay_order_id"],body.razorpay_payment_id,body.razorpay_signature,razorpay._settings.razorpay_key_secret):
        store.update_commerce_action(action["recommendation_id"],"failed",action["razorpay_order_id"],action)
        raise HTTPException(400,"Test payment verification failed.")
    store.update_commerce_action(action["recommendation_id"],"payment_verified",action["razorpay_order_id"],action)
    return {"status":"payment_verified","environment":"TEST MODE","action_id":action["action_id"]}

@router.get("/{recommendation_id}",response_model=CommerceAction)
def get_action(recommendation_id:str,store:AnalyticsStore=Depends(get_store)):
    action=store.get_commerce_action(recommendation_id)
    if not action: raise HTTPException(404,"Commerce action not found.")
    return CommerceAction(**action)

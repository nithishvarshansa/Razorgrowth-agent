from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.razorpay import RazorpayService, RazorpayServiceError

router = APIRouter(prefix="/api/razorpay", tags=["razorpay"])


def get_razorpay_service() -> RazorpayService:
    return RazorpayService()


def _collection_response(operation: str, service_call: Any) -> dict[str, Any]:
    try:
        return service_call()
    except RazorpayServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/orders")
def get_orders(
    count: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    service: RazorpayService = Depends(get_razorpay_service),
) -> dict[str, Any]:
    """Retrieve a bounded page of Razorpay Test Mode orders."""
    return _collection_response("orders", lambda: service.list_orders(count=count, skip=skip))


@router.get("/payments")
def get_payments(
    count: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    service: RazorpayService = Depends(get_razorpay_service),
) -> dict[str, Any]:
    """Retrieve a bounded page of Razorpay Test Mode payments."""
    return _collection_response("payments", lambda: service.list_payments(count=count, skip=skip))

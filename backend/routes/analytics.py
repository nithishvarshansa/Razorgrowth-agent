from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..routes.razorpay import get_razorpay_service
from ..services.analytics_store import AnalyticsStore
from ..services.analytics import summarize
from ..services.normalization import normalize_orders, normalize_payments
from ..services.opportunity_engine import analyze_opportunities
from ..services.razorpay import RazorpayService, RazorpayServiceError

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def get_store() -> AnalyticsStore:
    return AnalyticsStore()


@router.post("/sync")
def sync_test_mode_data(
    count: int = Query(default=100, ge=1, le=100),
    service: RazorpayService = Depends(get_razorpay_service),
    store: AnalyticsStore = Depends(get_store),
) -> dict[str, int]:
    """Fetch one bounded Test Mode page and persist normalized data locally."""
    try:
        orders = normalize_orders(service.list_orders(count, 0))
        payments = normalize_payments(service.list_payments(count, 0))
    except RazorpayServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    store.save(orders, payments)
    return {"normalized_orders": len(orders), "normalized_payments": len(payments)}


@router.get("")
def get_normalized_analytics(store: AnalyticsStore = Depends(get_store)) -> dict[str, Any]:
    orders, payments = store.load()
    return {"orders": [order.to_dict() for order in orders], "payments": [payment.to_dict() for payment in payments]}


@router.get("/summary")
def get_analytics_summary(store: AnalyticsStore = Depends(get_store)) -> dict[str, Any]:
    """Retrieve deterministic facts that are supported by stored Test Mode data."""
    orders, payments = store.load()
    return summarize(orders, payments)


@router.get("/opportunities")
def get_opportunities(store: AnalyticsStore = Depends(get_store)) -> dict[str, Any]:
    orders, payments = store.load()
    return analyze_opportunities(orders, payments)

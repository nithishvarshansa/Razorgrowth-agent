"""Deterministic summaries from normalized Razorpay Test Mode data."""
from collections import Counter
from typing import Any

from ..models.analytics import NormalizedOrder, NormalizedPayment


def summarize(orders: list[NormalizedOrder], payments: list[NormalizedPayment]) -> dict[str, Any]:
    """Return only facts supported by the normalized dataset.

    Amount totals are included only for captured payments with known amounts.
    Product and customer signals are omitted rather than inferred when unavailable.
    """
    captured = [payment for payment in payments if payment.success]
    failed = [payment for payment in payments if payment.failed]
    summary: dict[str, Any] = {
        "orders": {"count": len(orders)},
        "payments": {"count": len(payments), "captured_count": len(captured), "failed_count": len(failed)},
    }
    known_amounts = [payment.amount for payment in captured if payment.amount is not None]
    if known_amounts:
        summary["payments"]["captured_amount_total"] = sum(known_amounts)
    customer_counts = Counter(payment.customer_id for payment in captured if payment.customer_id)
    if customer_counts:
        summary["customers"] = {"identified_customer_count": len(customer_counts)}
    identified_products = {order.product_id or order.product_name for order in orders if order.product_id or order.product_name}
    if identified_products:
        summary["products"] = {"identified_product_count": len(identified_products)}
    return summary

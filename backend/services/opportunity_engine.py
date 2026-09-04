from collections import defaultdict
from typing import Any

from ..models.analytics import NormalizedOrder, NormalizedPayment


def analyze_opportunities(orders: list[NormalizedOrder], payments: list[NormalizedPayment]) -> dict[str, Any]:
    paid_order_ids = {payment.order_id for payment in payments if payment.success and payment.order_id}
    purchases = [order for order in orders if order.id in paid_order_ids and order.customer_id and (order.product_id or order.product_name)]
    if len(purchases) < 2:
        return {"status": "insufficient_data", "opportunities": [], "reason": "At least two successful, product-identified purchases are required."}

    by_customer: dict[str, list[NormalizedOrder]] = defaultdict(list)
    for purchase in purchases:
        by_customer[purchase.customer_id].append(purchase)
    opportunities: list[dict[str, Any]] = []
    product_key = lambda order: order.product_id or order.product_name
    all_products = {product_key(order) for order in purchases}
    for customer_id, customer_orders in by_customer.items():
        owned = {product_key(order) for order in customer_orders}
        candidates = sorted(all_products - owned)
        if candidates and any(len({product_key(o) for o in others}) > 1 for cid, others in by_customer.items() if cid != customer_id):
            candidate = candidates[0]
            opportunities.append({"opportunity_type": "cross_sell", "customer_id": customer_id, "recommended_product": candidate, "reason": "Other successful purchases show a product assortment beyond this customer's purchased product set.", "evidence": ["successful product-identified purchases"], "estimated_value": None, "confidence": "low"})
        by_product: dict[str, list[NormalizedOrder]] = defaultdict(list)
        for order in customer_orders:
            if order.amount is not None:
                by_product[product_key(order)].append(order)
        for product, history in by_product.items():
            amounts = {order.amount for order in history}
            if len(amounts) > 1:
                opportunities.append({"opportunity_type": "upsell", "customer_id": customer_id, "recommended_product": product, "reason": "This customer has successful purchases of the same identified product at more than one order value.", "evidence": [f"observed order values: {len(amounts)} distinct values"], "estimated_value": None, "confidence": "medium"})
    return {"status": "ready" if opportunities else "insufficient_data", "opportunities": opportunities, "reason": None if opportunities else "No supported upsell or cross-sell pattern was found."}

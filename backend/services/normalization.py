"""Defensive normalization of Razorpay collections; no product fields are invented."""
from typing import Any

from ..models.analytics import NormalizedOrder, NormalizedPayment


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _product(notes: Any) -> tuple[str | None, str | None]:
    if not isinstance(notes, dict):
        return None, None
    return _text(notes.get("product_id") or notes.get("sku")), _text(notes.get("product_name") or notes.get("product"))


def normalize_orders(payload: dict[str, Any]) -> list[NormalizedOrder]:
    normalized = []
    for item in _items(payload):
        identifier = _text(item.get("id"))
        if not identifier:
            continue
        product_id, product_name = _product(item.get("notes"))
        normalized.append(NormalizedOrder(identifier, _text(item.get("status")), _number(item.get("amount")), _text(item.get("currency")), _text(item.get("customer_id")), product_id, product_name, _number(item.get("created_at"))))
    return normalized


def normalize_payments(payload: dict[str, Any]) -> list[NormalizedPayment]:
    normalized = []
    for item in _items(payload):
        identifier = _text(item.get("id"))
        if not identifier:
            continue
        status = _text(item.get("status"))
        normalized.append(NormalizedPayment(identifier, _text(item.get("order_id")), status, _number(item.get("amount")), _text(item.get("currency")), _text(item.get("customer_id")), _number(item.get("created_at")), status == "captured", status == "failed"))
    return normalized

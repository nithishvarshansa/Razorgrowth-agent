from pathlib import Path

import pytest

from backend.models.analytics import NormalizedOrder, NormalizedPayment
from backend.services.analytics_store import AnalyticsStore
from backend.services.analytics import summarize
from backend.services.normalization import normalize_orders, normalize_payments
from backend.services.opportunity_engine import analyze_opportunities
from backend.services.razorpay import RazorpayServiceError


def test_normalization_discards_malformed_items():
    orders = normalize_orders({"items": [{"id": "order_1", "amount": 100, "notes": {"product_id": "sku-a"}}, {"amount": 200}, "bad"]})
    payments = normalize_payments({"items": [{"id": "pay_1", "order_id": "order_1", "status": "captured"}, {}]})
    assert orders[0].product_id == "sku-a"
    assert payments[0].success is True
    assert len(orders) == len(payments) == 1


def test_empty_dataset_is_insufficient():
    assert analyze_opportunities([], [])["status"] == "insufficient_data"


def test_empty_orders_and_payments_normalize_to_empty_lists():
    assert normalize_orders({"items": []}) == []
    assert normalize_payments({"items": []}) == []


def test_analytics_calculates_only_supported_payment_facts():
    payment = NormalizedPayment("p1", None, "captured", 500, "INR", "customer_1", 1, True, False)
    summary = summarize([], [payment])
    assert summary["payments"]["captured_amount_total"] == 500
    assert "products" not in summary


def test_missing_customer_and_product_data_does_not_create_metrics():
    order = NormalizedOrder("o1", "created", 100, "INR", None, None, None, 1)
    payment = NormalizedPayment("p1", "o1", "failed", 100, "INR", None, 1, False, True)
    summary = summarize([order], [payment])
    assert "customers" not in summary
    assert "products" not in summary


def test_cross_sell_detection_uses_only_test_fixture_evidence():
    orders = [NormalizedOrder("o1", "paid", 100, "INR", "c1", "a", None, 1), NormalizedOrder("o2", "paid", 100, "INR", "c2", "a", None, 2), NormalizedOrder("o3", "paid", 100, "INR", "c2", "b", None, 3)]
    payments = [NormalizedPayment(f"p{i}", order.id, "captured", 100, "INR", order.customer_id, 1, True, False) for i, order in enumerate(orders)]
    result = analyze_opportunities(orders, payments)
    assert any(item["opportunity_type"] == "cross_sell" and item["customer_id"] == "c1" for item in result["opportunities"])


def test_upsell_detection_requires_distinct_observed_values():
    orders = [NormalizedOrder("o1", "paid", 100, "INR", "c1", "a", None, 1), NormalizedOrder("o2", "paid", 200, "INR", "c1", "a", None, 2)]
    payments = [NormalizedPayment(f"p{i}", order.id, "captured", order.amount, "INR", "c1", 1, True, False) for i, order in enumerate(orders)]
    result = analyze_opportunities(orders, payments)
    assert any(item["opportunity_type"] == "upsell" for item in result["opportunities"])


def test_store_round_trip(tmp_path: Path):
    store = AnalyticsStore(f"sqlite:///./{tmp_path / 'analytics.db'}")
    order = NormalizedOrder("o1", None, None, None, None, None, None, None)
    payment = NormalizedPayment("p1", "o1", "failed", None, None, None, None, False, True)
    store.save([order], [payment])
    assert store.load() == ([order], [payment])


def test_razorpay_failure_can_be_propagated_safely():
    error = RazorpayServiceError(502, "Razorpay API request failed.")
    assert error.status_code == 502
    assert "secret" not in error.message.lower()

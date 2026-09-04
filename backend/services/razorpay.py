"""Server-side, read-only access to Razorpay Test Mode collection endpoints."""

from collections.abc import Callable
from typing import Any

import httpx

from ..config import Settings, get_settings

RAZORPAY_API_BASE_URL = "https://api.razorpay.com/v1"


class RazorpayServiceError(Exception):
    """A safe error intended for API consumers; it never includes credentials."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class RazorpayService:
    def __init__(
        self,
        settings: Settings | None = None,
        requester: Callable[..., httpx.Response] = httpx.request,
    ) -> None:
        self._settings = settings or get_settings()
        self._requester = requester

    def list_orders(self, count: int, skip: int) -> dict[str, Any]:
        return self._get_collection("/orders", count, skip)

    def list_payments(self, count: int, skip: int) -> dict[str, Any]:
        return self._get_collection("/payments", count, skip)

    def create_test_order(self, amount: int, currency: str, receipt: str, notes: dict[str, str]) -> dict[str, Any]:
        if amount <= 0 or len(currency) != 3 or not currency.isalpha():
            raise RazorpayServiceError(400, "A valid test amount and currency are required.")
        return self._request("POST", "/orders", json={"amount": amount, "currency": currency.upper(), "receipt": receipt, "notes": notes})

    def _get_collection(self, path: str, count: int, skip: int) -> dict[str, Any]:
        return self._request("GET", path, params={"count": count, "skip": skip})

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        key_id = self._settings.razorpay_key_id
        key_secret = self._settings.razorpay_key_secret
        if not key_id or not key_secret:
            raise RazorpayServiceError(503, "Razorpay test-mode credentials are not configured.")
        if not key_id.startswith("rzp_test_"):
            raise RazorpayServiceError(503, "Only Razorpay test-mode credentials can be used.")

        try:
            response = self._requester(
                method,
                f"{RAZORPAY_API_BASE_URL}{path}",
                auth=(key_id, key_secret),
                timeout=self._settings.razorpay_timeout_seconds,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise RazorpayServiceError(504, "Razorpay request timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise RazorpayServiceError(502, "Unable to reach Razorpay. Please try again.") from exc

        if response.status_code in (401, 403):
            raise RazorpayServiceError(502, "Razorpay authentication failed.")
        if response.is_error:
            raise RazorpayServiceError(502, "Razorpay API request failed.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise RazorpayServiceError(502, "Razorpay returned an invalid response.") from exc
        if not isinstance(payload, dict):
            raise RazorpayServiceError(502, "Razorpay returned an invalid response.")
        return payload

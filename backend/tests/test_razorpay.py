import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import BACKEND_ENV_FILE, Settings
from backend.routes.razorpay import get_razorpay_service
from backend.services.razorpay import RazorpayService, RazorpayServiceError


def test_configuration_loads_test_mode_credentials_without_exposing_them():
    settings = Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="secret")
    assert settings.razorpay_key_id == "rzp_test_key"
    assert settings.razorpay_key_secret == "secret"


def test_configuration_uses_the_backend_dotenv_file_independent_of_working_directory():
    assert Settings.model_config["env_file"] == str(BACKEND_ENV_FILE)
    assert BACKEND_ENV_FILE.name == ".env"


def test_missing_credentials_are_handled_safely():
    service = RazorpayService(settings=Settings(_env_file=None))
    with pytest.raises(RazorpayServiceError, match="not configured") as error:
        service.list_orders(10, 0)
    assert error.value.status_code == 503


def test_successful_orders_response_uses_authenticated_read_only_request():
    captured = {}
    def requester(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"entity": "collection", "count": 0, "items": []})

    service = RazorpayService(Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="secret"), requester)
    assert service.list_orders(5, 2) == {"entity": "collection", "count": 0, "items": []}
    assert captured["url"].endswith("/v1/orders")
    assert captured["method"] == "GET"
    assert captured["params"] == {"count": 5, "skip": 2}
    assert captured["auth"] == ("rzp_test_key", "secret")


def test_razorpay_api_error_is_safe():
    service = RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="secret"),
        lambda *args, **kwargs: httpx.Response(400, json={"error": {"description": "unsafe upstream detail"}}),
    )
    with pytest.raises(RazorpayServiceError, match="API request failed") as error:
        service.list_payments(10, 0)
    assert error.value.status_code == 502


def test_timeout_is_safe():
    def requester(*args, **kwargs):
        raise httpx.TimeoutException("timeout")
    service = RazorpayService(Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret="secret"), requester)
    with pytest.raises(RazorpayServiceError, match="timed out") as error:
        service.list_payments(10, 0)
    assert error.value.status_code == 504


def test_route_never_returns_credentials():
    secret = "very-private-secret"
    app = create_app()
    app.dependency_overrides[get_razorpay_service] = lambda: RazorpayService(
        Settings(_env_file=None, razorpay_key_id="rzp_test_key", razorpay_key_secret=secret),
        lambda *args, **kwargs: httpx.Response(200, json={"entity": "collection", "count": 0, "items": []}),
    )
    response = TestClient(app).get("/api/razorpay/payments")
    assert response.status_code == 200
    assert secret not in response.text
    assert "rzp_test_key" not in response.text

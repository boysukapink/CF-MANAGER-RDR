"""Unit tests for Cloudflare HTTP Client with mocked API responses.
No live production tokens or network calls are made.
"""

from unittest.mock import MagicMock, patch
import pytest
import httpx
from src.cloudflare.client import CloudflareClient
from src.cloudflare.zones import fetch_all_zones
from src.cloudflare.redirects import delete_redirect_rule
from src.security.session import active_session
from src.utils.errors import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    NetworkError,
    ValidationError,
)


@pytest.fixture(autouse=True)
def setup_dummy_session():
    active_session.set_token("dummy_testing_token_abcdef123456")
    yield
    active_session.disconnect()


def test_client_http_401():
    client = CloudflareClient()
    mock_resp = httpx.Response(401, json={"success": False, "errors": [{"message": "Invalid token"}]})

    with patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(AuthenticationError):
            client.request("GET", "user/tokens/verify")


def test_client_http_403():
    client = CloudflareClient()
    mock_resp = httpx.Response(403, json={"success": False, "errors": [{"message": "Access denied"}]})

    with patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(ForbiddenError):
            client.request("GET", "zones")


def test_client_http_404():
    client = CloudflareClient()
    mock_resp = httpx.Response(404, json={"success": False, "errors": [{"message": "Not found"}]})

    with patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(NotFoundError):
            client.request("GET", "zones/nonexistent")


def test_client_http_429_rate_limit():
    client = CloudflareClient()
    mock_resp = httpx.Response(
        429,
        headers={"Retry-After": "30"},
        json={"success": False, "errors": [{"message": "Rate limit exceeded"}]}
    )

    with patch.object(httpx.Client, "request", return_value=mock_resp):
        with pytest.raises(RateLimitError) as exc_info:
            client.request("GET", "zones")
        assert exc_info.value.retry_after == 30


def test_client_timeout_network_error():
    client = CloudflareClient()

    with patch.object(httpx.Client, "request", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(NetworkError, match="Timeout"):
            client.request("GET", "zones")


def test_fetch_all_zones_pagination():
    page1 = {
        "success": True,
        "result": [{"id": "z1", "name": "alpha.com", "status": "active"}],
        "result_info": {"page": 1, "total_pages": 2}
    }
    page2 = {
        "success": True,
        "result": [{"id": "z2", "name": "beta.com", "status": "active"}],
        "result_info": {"page": 2, "total_pages": 2}
    }

    mock_client = MagicMock()
    mock_client.request.side_effect = [page1, page2]

    with patch("src.cloudflare.zones.cf_client", mock_client):
        zones = fetch_all_zones()
        assert len(zones) == 2
        assert zones[0].name == "alpha.com"
        assert zones[1].name == "beta.com"


def test_delete_redirect_safety_missing_params():
    with pytest.raises(ValidationError):
        delete_redirect_rule("", "ruleset1", "rule1")

    with pytest.raises(ValidationError):
        delete_redirect_rule("zone1", "", "rule1")

    with pytest.raises(ValidationError):
        delete_redirect_rule("zone1", "ruleset1", "")


def test_delete_redirect_dry_run():
    res = delete_redirect_rule("zone1", "ruleset1", "rule1", dry_run=True)
    assert res["dry_run"] is True
    assert res["rule_id"] == "rule1"


def test_delete_redirect_rule_reverification_not_found():
    # If rule is no longer present on zone, it should raise NotFoundError
    with patch("src.cloudflare.redirects.get_zone_redirect_ruleset", return_value=("ruleset1", [])):
        with pytest.raises(NotFoundError, match="tidak ditemukan lagi"):
            delete_redirect_rule("zone1", "ruleset1", "rule_not_exist")


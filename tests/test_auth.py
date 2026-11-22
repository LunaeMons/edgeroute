"""Tests for the admin token check (``app.auth``) on every endpoint that needs it.

The admin endpoints are listed once in ``ADMIN_ENDPOINTS``; each test runs against all
of them (``pytest.mark.parametrize``), so a new admin endpoint only needs adding there.
"""

from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth
from app.config import get_settings
from tests.conftest import MakeCdn

# A probe export with one valid row: if authentication were bypassed, it would be stored.
PROBE_CSV = "timestamp,cdn_name,region,status,ttfb\n2026-11-17 08:00:00,aurora,eu-west,200,120ms\n"

# (HTTP method, path, request arguments, status with the right token) for every admin
# endpoint. Each test first registers one CDN, "kestrel", which gets ID 1.
ADMIN_ENDPOINTS: list[tuple[str, str, dict[str, Any], int]] = [
    ("POST", "/api/v1/cdns", {"json": {"name": "aurora", "base_url": "https://a.example"}}, 201),
    ("PATCH", "/api/v1/cdns/1", {"json": {"weight": 5}}, 200),
    ("DELETE", "/api/v1/cdns/1", {}, 204),
    ("POST", "/api/v1/probes/import", {"files": {"file": ("p.csv", PROBE_CSV, "text/csv")}}, 200),
]

# (path, query parameters) for every public endpoint.
PUBLIC_ENDPOINTS: list[tuple[str, dict[str, str]]] = [
    ("/healthz", {}),
    ("/api/v1/cdns", {}),
    ("/api/v1/probes/health/eu-west", {}),
]

# Readable test names in pytest's output, e.g. "POST /api/v1/cdns".
ADMIN_IDS = [f"{method} {path}" for method, path, _, _ in ADMIN_ENDPOINTS]
PARAMS = ("method", "path", "kwargs", "expected_status")


def _assert_nothing_changed(client: TestClient, kestrel: dict[str, Any]) -> None:
    """Check that a rejected request left the CDNs and the probes untouched.

    Args:
        client: Test client.
        kestrel: The CDN registered before the request, as the API returned it.
    """
    assert client.get("/api/v1/cdns").json() == [kestrel]
    assert client.get("/api/v1/probes/health/eu-west").json()["providers"] == {}


@pytest.mark.parametrize(PARAMS, ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_without_token_is_rejected(
    client: TestClient,
    make_cdn: MakeCdn,
    method: str,
    path: str,
    kwargs: dict[str, Any],
    expected_status: int,
) -> None:
    """A request without the ``X-Admin-Token`` header fails with 422 and changes nothing.

    The response says which header is missing, so the caller knows how to fix it.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
        expected_status: Status with the right token (unused here).
    """
    kestrel = make_cdn(name="kestrel")

    response = client.request(method, path, **kwargs)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["header", "x-admin-token"]
    _assert_nothing_changed(client, kestrel)


@pytest.mark.parametrize(PARAMS, ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_with_wrong_token_is_rejected(
    client: TestClient,
    make_cdn: MakeCdn,
    method: str,
    path: str,
    kwargs: dict[str, Any],
    expected_status: int,
) -> None:
    """A request with the wrong token gets 401 Unauthorized and changes nothing.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
        expected_status: Status with the right token (unused here).
    """
    kestrel = make_cdn(name="kestrel")

    response = client.request(method, path, headers={"X-Admin-Token": "wrong"}, **kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin token."}
    _assert_nothing_changed(client, kestrel)


@pytest.mark.parametrize(PARAMS, ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_with_the_right_token_succeeds(
    client: TestClient,
    make_cdn: MakeCdn,
    admin_headers: dict[str, str],
    method: str,
    path: str,
    kwargs: dict[str, Any],
    expected_status: int,
) -> None:
    """With the right token, the same request is carried out.

    This is the counterpart of the two tests above: it proves those requests are
    rejected because of the token, not because the request itself is wrong.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
        expected_status: The success status the endpoint answers with.
    """
    make_cdn(name="kestrel")

    response = client.request(method, path, headers=admin_headers, **kwargs)

    assert response.status_code == expected_status


@pytest.mark.parametrize(("path", "params"), PUBLIC_ENDPOINTS, ids=[p for p, _ in PUBLIC_ENDPOINTS])
def test_public_endpoints_need_no_token(
    client: TestClient, path: str, params: dict[str, str]
) -> None:
    """Read-only endpoints answer 200 without any token.

    Args:
        client: Test client with a fresh database.
        path: Path of the endpoint.
        params: Query parameters the endpoint needs.
    """
    assert client.get(path, params=params).status_code == 200


def test_require_admin_accepts_the_configured_token() -> None:
    """Called directly with the configured token, the check passes and returns None."""
    assert auth.require_admin(get_settings().admin_token) is None


@pytest.mark.parametrize("token", ["wrong", "", " changeme", "CHANGEME"])
def test_require_admin_rejects_any_other_token(token: str) -> None:
    """Any other value, including near misses, raises a 401 HTTPException.

    Args:
        token: A token that differs from the configured one.
    """
    with pytest.raises(HTTPException) as caught:
        auth.require_admin(token)

    assert caught.value.status_code == 401
    assert caught.value.detail == "Invalid admin token."

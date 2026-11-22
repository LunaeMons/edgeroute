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

# (HTTP method, path, extra arguments for the request) for every admin endpoint.
ADMIN_ENDPOINTS: list[tuple[str, str, dict[str, Any]]] = [
    ("POST", "/api/v1/cdns", {"json": {"name": "aurora", "base_url": "https://a.example"}}),
    ("PATCH", "/api/v1/cdns/1", {"json": {"weight": 5}}),
    ("DELETE", "/api/v1/cdns/1", {}),
    ("POST", "/api/v1/probes/import", {"files": {"file": ("p.csv", "a,b\n", "text/csv")}}),
]

# (path, query parameters) for every public endpoint.
PUBLIC_ENDPOINTS: list[tuple[str, dict[str, str]]] = [
    ("/healthz", {}),
    ("/api/v1/cdns", {}),
    ("/api/v1/probes/health/eu-west", {}),
]

# Readable test names in pytest's output, e.g. "POST /api/v1/cdns".
ADMIN_IDS = [f"{method} {path}" for method, path, _ in ADMIN_ENDPOINTS]


@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_without_token_is_rejected(
    client: TestClient, method: str, path: str, kwargs: dict[str, Any]
) -> None:
    """A request without the ``X-Admin-Token`` header fails validation with 422.

    The response says which header is missing, so the caller knows how to fix it.

    Args:
        client: Test client with a fresh database.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
    """
    response = client.request(method, path, **kwargs)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["header", "x-admin-token"]


@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_with_wrong_token_is_rejected(
    client: TestClient, method: str, path: str, kwargs: dict[str, Any]
) -> None:
    """A request with the wrong token gets 401 Unauthorized and changes nothing.

    Args:
        client: Test client with a fresh database.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
    """
    response = client.request(method, path, headers={"X-Admin-Token": "wrong"}, **kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin token."}
    assert client.get("/api/v1/cdns").json() == []


@pytest.mark.parametrize(("method", "path", "kwargs"), ADMIN_ENDPOINTS, ids=ADMIN_IDS)
def test_admin_endpoint_with_the_right_token_is_let_through(
    client: TestClient,
    admin_headers: dict[str, str],
    method: str,
    path: str,
    kwargs: dict[str, Any],
) -> None:
    """With the right token, the request reaches the endpoint itself.

    The endpoint may still refuse the request for its own reasons (PATCH and DELETE on
    a CDN that does not exist answer 404), but never with 401 or a missing-header 422.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
        method: HTTP method of the endpoint.
        path: Path of the endpoint.
        kwargs: Body or files the endpoint expects.
    """
    response = client.request(method, path, headers=admin_headers, **kwargs)

    assert response.status_code in {200, 201, 204, 404}


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

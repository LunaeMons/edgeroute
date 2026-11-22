"""Tests for the CDN provider endpoints (``/api/v1/cdns``).

Each test follows the same shape: set up the data it needs, make one request, then
check the response.
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

MakeCdn = Callable[..., dict[str, Any]]


def test_list_is_empty_on_a_new_database(client: TestClient) -> None:
    """A brand-new database has no CDNs, and listing them returns an empty list.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/api/v1/cdns")

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_fetch(client: TestClient, make_cdn: MakeCdn) -> None:
    """A CDN that was created can be fetched back by its ID, with the values sent.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
    """
    created = make_cdn(name="aurora", weight=40)

    response = client.get(f"/api/v1/cdns/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "aurora"
    assert body["weight"] == 40
    # ``enabled`` was not sent, so it should take its default value.
    assert body["enabled"] is True


def test_create_requires_admin_token(client: TestClient) -> None:
    """Creating a CDN with a wrong admin token is refused with 401 Unauthorized.

    Args:
        client: Test client with a fresh database.
    """
    response = client.post(
        "/api/v1/cdns",
        json={"name": "aurora", "base_url": "https://cdn.example"},
        headers={"X-Admin-Token": "wrong"},
    )

    assert response.status_code == 401


def test_duplicate_name_is_rejected(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """Registering a second CDN with an existing name is refused with 409 Conflict.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    make_cdn(name="aurora")

    response = client.post(
        "/api/v1/cdns",
        json={"name": "aurora", "base_url": "https://other.example"},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_invalid_name_is_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    """A name with capitals, spaces or punctuation fails validation with 422.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.post(
        "/api/v1/cdns",
        json={"name": "Not Valid!", "base_url": "https://cdn.example"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_disable_a_cdn(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """A CDN can be switched off with a partial update, and the change is returned.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="kestrel")

    response = client.patch(
        f"/api/v1/cdns/{created['id']}", json={"enabled": False}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_update_unknown_cdn_returns_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Updating a CDN that does not exist returns 404 Not Found.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.patch("/api/v1/cdns/999", json={"weight": 5}, headers=admin_headers)

    assert response.status_code == 404


def test_delete(client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]) -> None:
    """A deleted CDN is gone: deleting returns 204, then fetching it returns 404.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="meridian")

    delete_response = client.delete(f"/api/v1/cdns/{created['id']}", headers=admin_headers)

    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/cdns/{created['id']}").status_code == 404

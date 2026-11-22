"""Tests for the CDN provider endpoints (``/api/v1/cdns``).

Each test follows the same shape, separated by blank lines: set up the data it needs,
make one request, then check the response and, where it matters, the stored state.
Authentication is tested separately, for every admin endpoint, in ``test_auth.py``.
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MakeCdn

VALID = {"name": "aurora", "base_url": "https://cdn.example"}


# --- Create -------------------------------------------------------------------------


def test_create_returns_the_stored_cdn(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Creating a CDN answers 201 with every field, including the generated ones.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    payload = {
        "name": "aurora",
        "base_url": "https://nw.aurora-edge.example",
        "weight": 40,
        "enabled": False,
        "cost_per_gb_cents": 4,
    }

    response = client.post("/api/v1/cdns", json=payload, headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    created_at = body.pop("created_at")
    assert body == {
        "id": 1,
        "name": "aurora",
        # pydantic normalises URLs: a bare host gets a trailing slash.
        "base_url": "https://nw.aurora-edge.example/",
        "weight": 40,
        "enabled": False,
        "cost_per_gb_cents": 4,
    }
    # The database fills in the creation time; check it is a valid ISO 8601 timestamp
    # rather than its exact value, which depends on when the test runs.
    datetime.fromisoformat(created_at)


def test_create_applies_the_defaults(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Fields left out get their defaults: weight 1, enabled, no cost.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.post("/api/v1/cdns", json=VALID, headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    del body["created_at"]
    assert body == {
        "id": 1,
        "name": "aurora",
        "base_url": "https://cdn.example/",
        "weight": 1,
        "enabled": True,
        "cost_per_gb_cents": None,
    }


@pytest.mark.parametrize("weight", [0, 100])
def test_create_accepts_the_weight_limits(
    client: TestClient, admin_headers: dict[str, str], weight: int
) -> None:
    """Weights of exactly 0 and 100, the edges of the allowed range, are accepted.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
        weight: A weight at the edge of the range.
    """
    response = client.post("/api/v1/cdns", json=VALID | {"weight": weight}, headers=admin_headers)

    assert response.status_code == 201
    assert response.json()["weight"] == weight


def test_create_accepts_a_name_of_64_characters(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """The longest allowed name (64 characters) is accepted.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.post("/api/v1/cdns", json=VALID | {"name": "a" * 64}, headers=admin_headers)

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "a" * 65),
        ("name", "Aurora"),
        ("name", "aurora edge"),
        ("name", "aurora_edge"),
        ("name", "Not Valid!"),
        ("base_url", "not-a-url"),
        ("base_url", ""),
        ("weight", -1),
        ("weight", 101),
        ("weight", "heavy"),
        ("cost_per_gb_cents", -1),
    ],
)
def test_create_rejects_invalid_values(
    client: TestClient, admin_headers: dict[str, str], field: str, value: Any
) -> None:
    """Each invalid value is refused with 422, the error names the field, nothing is stored.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
        field: The field given an invalid value.
        value: The invalid value.
    """
    response = client.post("/api/v1/cdns", json=VALID | {field: value}, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert client.get("/api/v1/cdns").json() == []


@pytest.mark.parametrize("missing", ["name", "base_url"])
def test_create_rejects_a_missing_required_field(
    client: TestClient, admin_headers: dict[str, str], missing: str
) -> None:
    """Leaving out the name or the base URL is refused with 422 naming the field.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
        missing: The required field left out.
    """
    payload = {key: value for key, value in VALID.items() if key != missing}

    response = client.post("/api/v1/cdns", json=payload, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing]


def test_duplicate_name_is_rejected(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """A second CDN with an existing name is refused with 409, and the first is kept.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    make_cdn(name="aurora", base_url="https://first.example")

    response = client.post(
        "/api/v1/cdns",
        json={"name": "aurora", "base_url": "https://other.example"},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "CDN 'aurora' already exists."}
    stored = client.get("/api/v1/cdns").json()
    assert [(cdn["name"], cdn["base_url"]) for cdn in stored] == [
        ("aurora", "https://first.example/")
    ]


# --- Read ---------------------------------------------------------------------------


def test_list_is_empty_on_a_new_database(client: TestClient) -> None:
    """A brand-new database has no CDNs, and listing them returns an empty list.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/api/v1/cdns")

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_every_cdn_ordered_by_name(client: TestClient, make_cdn: MakeCdn) -> None:
    """The list contains every CDN, sorted by name whatever the creation order.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
    """
    for name in ["meridian", "aurora", "kestrel"]:
        make_cdn(name=name)

    response = client.get("/api/v1/cdns")

    assert response.status_code == 200
    assert [cdn["name"] for cdn in response.json()] == ["aurora", "kestrel", "meridian"]


def test_fetch_returns_the_same_cdn_as_create(client: TestClient, make_cdn: MakeCdn) -> None:
    """Fetching a CDN by ID returns exactly what the create call returned.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
    """
    created = make_cdn(name="aurora", weight=40, cost_per_gb_cents=4)

    response = client.get(f"/api/v1/cdns/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_fetch_unknown_cdn_returns_404(client: TestClient) -> None:
    """Fetching a CDN that does not exist returns 404 with a clear message.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/api/v1/cdns/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "CDN not found."}


def test_fetch_with_a_non_numeric_id_returns_422(client: TestClient) -> None:
    """An ID that is not a number is refused by validation before any lookup.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/api/v1/cdns/aurora")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "cdn_id"]


# --- Update -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"weight": 5}, {"weight": 5}),
        ({"enabled": False}, {"enabled": False}),
        ({"base_url": "https://new.example/edge"}, {"base_url": "https://new.example/edge"}),
        ({"cost_per_gb_cents": 7}, {"cost_per_gb_cents": 7}),
    ],
    ids=["weight", "enabled", "base_url", "cost"],
)
def test_update_changes_only_the_fields_sent(
    client: TestClient,
    make_cdn: MakeCdn,
    admin_headers: dict[str, str],
    change: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """A partial update changes the fields sent and leaves every other field as it was.

    The change is checked twice: in the response, and by fetching the CDN again, to
    prove it was stored and not only echoed back.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
        change: The request body.
        expected: The fields that must have changed.
    """
    created = make_cdn(name="kestrel", weight=20, cost_per_gb_cents=2)

    response = client.patch(f"/api/v1/cdns/{created['id']}", json=change, headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == created | expected
    assert client.get(f"/api/v1/cdns/{created['id']}").json() == created | expected


def test_disabled_cdn_can_be_enabled_again(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """Switching a CDN off and on again leaves it enabled.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="kestrel", enabled=False)

    response = client.patch(
        f"/api/v1/cdns/{created['id']}", json={"enabled": True}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json() == created | {"enabled": True}
    assert client.get(f"/api/v1/cdns/{created['id']}").json() == created | {"enabled": True}


def test_update_with_an_empty_body_changes_nothing(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """An update with no fields is accepted and returns the CDN unchanged.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="kestrel")

    response = client.patch(f"/api/v1/cdns/{created['id']}", json={}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == created


def test_update_cannot_rename_a_cdn(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """The name is not an updatable field: sending one leaves the name unchanged.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="kestrel")

    response = client.patch(
        f"/api/v1/cdns/{created['id']}", json={"name": "renamed"}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json() == created
    assert client.get(f"/api/v1/cdns/{created['id']}").json() == created


@pytest.mark.parametrize(
    ("field", "value"),
    [("weight", -1), ("weight", 101), ("base_url", "not-a-url"), ("cost_per_gb_cents", -5)],
)
def test_update_rejects_invalid_values(
    client: TestClient,
    make_cdn: MakeCdn,
    admin_headers: dict[str, str],
    field: str,
    value: Any,
) -> None:
    """An invalid value is refused with 422 and the stored CDN is not changed.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
        field: The field given an invalid value.
        value: The invalid value.
    """
    created = make_cdn(name="kestrel")

    response = client.patch(
        f"/api/v1/cdns/{created['id']}", json={field: value}, headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert client.get(f"/api/v1/cdns/{created['id']}").json() == created


def test_update_unknown_cdn_returns_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Updating a CDN that does not exist returns 404 and creates nothing.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.patch("/api/v1/cdns/999", json={"weight": 5}, headers=admin_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "CDN not found."}
    assert client.get("/api/v1/cdns").json() == []


# --- Delete -------------------------------------------------------------------------


def test_delete_removes_only_that_cdn(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """Deleting answers 204 with no body; the CDN is gone and the others remain.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    doomed = make_cdn(name="meridian")
    make_cdn(name="aurora")

    response = client.delete(f"/api/v1/cdns/{doomed['id']}", headers=admin_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/v1/cdns/{doomed['id']}").status_code == 404
    assert [cdn["name"] for cdn in client.get("/api/v1/cdns").json()] == ["aurora"]


def test_delete_twice_returns_404_the_second_time(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """A CDN can only be deleted once; deleting it again returns 404.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="meridian")
    client.delete(f"/api/v1/cdns/{created['id']}", headers=admin_headers)

    response = client.delete(f"/api/v1/cdns/{created['id']}", headers=admin_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "CDN not found."}


def test_a_deleted_name_can_be_registered_again(
    client: TestClient, make_cdn: MakeCdn, admin_headers: dict[str, str]
) -> None:
    """Once a CDN is deleted, its name is free to use again.

    Args:
        client: Test client with a fresh database.
        make_cdn: Factory that registers a CDN.
        admin_headers: Admin authentication headers.
    """
    created = make_cdn(name="meridian")
    client.delete(f"/api/v1/cdns/{created['id']}", headers=admin_headers)

    response = client.post(
        "/api/v1/cdns",
        json={"name": "meridian", "base_url": "https://m.example"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "meridian"
    assert response.json()["base_url"] == "https://m.example/"
    assert [cdn["name"] for cdn in client.get("/api/v1/cdns").json()] == ["meridian"]

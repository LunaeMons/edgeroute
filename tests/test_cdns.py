"""Tests for the CDN provider endpoints."""


def test_list_is_empty_on_a_new_database(client):
    response = client.get("/api/v1/cdns")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_fetch(client, make_cdn):
    created = make_cdn(name="aurora", weight=40)
    response = client.get(f"/api/v1/cdns/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "aurora"
    assert body["weight"] == 40
    assert body["enabled"] is True


def test_create_requires_admin_token(client):
    response = client.post(
        "/api/v1/cdns",
        json={"name": "aurora", "base_url": "https://cdn.example"},
        headers={"X-Admin-Token": "wrong"},
    )
    assert response.status_code == 401


def test_duplicate_name_is_rejected(client, make_cdn, admin_headers):
    make_cdn(name="aurora")
    response = client.post(
        "/api/v1/cdns",
        json={"name": "aurora", "base_url": "https://other.example"},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_invalid_name_is_rejected(client, admin_headers):
    response = client.post(
        "/api/v1/cdns",
        json={"name": "Not Valid!", "base_url": "https://cdn.example"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_disable_a_cdn(client, make_cdn, admin_headers):
    created = make_cdn(name="kestrel")
    response = client.patch(
        f"/api/v1/cdns/{created['id']}", json={"enabled": False}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_update_unknown_cdn_returns_404(client, admin_headers):
    response = client.patch("/api/v1/cdns/999", json={"weight": 5}, headers=admin_headers)
    assert response.status_code == 404


def test_delete(client, make_cdn, admin_headers):
    created = make_cdn(name="meridian")
    assert client.delete(f"/api/v1/cdns/{created['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/v1/cdns/{created['id']}").status_code == 404

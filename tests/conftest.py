"""Shared test fixtures."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ADMIN = {"X-Admin-Token": "changeme"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A test client backed by a fresh database file."""
    monkeypatch.setenv("EDGEROUTE_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers():
    """Headers that authenticate as an admin."""
    return ADMIN


@pytest.fixture()
def make_cdn(client, admin_headers):
    """Factory that registers a CDN through the API."""

    def _make(name="aurora", weight=50, enabled=True, base_url="https://cdn.example"):
        response = client.post(
            "/api/v1/cdns",
            json={"name": name, "base_url": base_url, "weight": weight, "enabled": enabled},
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make

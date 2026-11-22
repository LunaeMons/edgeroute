"""Tests for the application factory and the operational endpoints (``app.main``)."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_reports_ok(client: TestClient) -> None:
    """The liveness endpoint answers 200 with ``{"status": "ok"}``.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_builds_a_new_app_each_time() -> None:
    """Each call returns a separate application, so tests never share state."""
    assert create_app() is not create_app()


def test_every_feature_is_registered(client: TestClient) -> None:
    """The OpenAPI document lists the endpoints of every feature.

    If a router is not included in ``create_app``, its endpoints silently disappear;
    this test catches that.

    Args:
        client: Test client with a fresh database.
    """
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths) == {
        "/api/v1/cdns",
        "/api/v1/cdns/{cdn_id}",
        "/api/v1/steer",
        "/api/v1/probes/import",
        "/api/v1/probes/health/{region}",
        "/healthz",
    }


def test_unknown_path_returns_404(client: TestClient) -> None:
    """A path the app does not serve answers 404 Not Found.

    Args:
        client: Test client with a fresh database.
    """
    assert client.get("/api/v1/nope").status_code == 404

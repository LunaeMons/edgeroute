"""Shared test fixtures.

pytest loads this file automatically. A *fixture* is a function that prepares something
a test needs. A test asks for one simply by naming it as a parameter, and pytest runs
the fixture and passes in the result. For example, ``def test_x(client):`` receives a
ready-to-use HTTP client.

Each test gets its own fresh database, so tests never depend on each other or on the
order they run in.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

# Headers that authenticate as an admin. The value matches the token the app falls back
# to when none is configured (see app/config.py).
ADMIN = {"X-Admin-Token": "changeme"}


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Provide an HTTP client for the app, backed by a fresh database file.

    ``TestClient`` calls the app directly in memory, without starting a web server, so
    tests are fast and need no network.

    Args:
        tmp_path: A temporary directory that pytest creates for this test (built-in
            fixture).
        monkeypatch: Lets the test change environment variables; pytest undoes the
            changes when the test ends (built-in fixture).

    Yields:
        A client whose requests go to a newly created app.
    """
    # Point the app at an empty database inside this test's temporary directory.
    monkeypatch.setenv("EDGEROUTE_DB_PATH", str(tmp_path / "test.db"))
    # Using the client as a context manager runs the app's start-up code, which creates
    # the tables.
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    """Provide the headers that authenticate a request as an admin.

    Returns:
        A dictionary with the ``X-Admin-Token`` header.
    """
    return ADMIN


@pytest.fixture()
def make_cdn(client: TestClient, admin_headers: dict[str, str]) -> Callable[..., dict[str, Any]]:
    """Provide a function that registers a CDN through the API.

    A fixture that returns a function (a *factory*) lets one test create as many CDNs
    as it needs, each with different values.

    Args:
        client: The test client (fixture above).
        admin_headers: Admin authentication headers (fixture above).

    Returns:
        A function that creates a CDN and returns it as the API sent it back.
    """

    def _make(
        name: str = "aurora",
        weight: int = 50,
        enabled: bool = True,
        base_url: str = "https://cdn.example",
    ) -> dict[str, Any]:
        """Register one CDN and fail the test straight away if that does not work.

        Args:
            name: The CDN's unique name.
            weight: Its share of traffic, from 0 to 100.
            enabled: Whether it may receive traffic.
            base_url: The root URL its assets are served from.

        Returns:
            The created CDN, as returned by the API.
        """
        response = client.post(
            "/api/v1/cdns",
            json={"name": name, "base_url": base_url, "weight": weight, "enabled": enabled},
            headers=admin_headers,
        )
        # The second part of the assert is the message pytest shows if it fails.
        assert response.status_code == 201, response.text
        return response.json()

    return _make

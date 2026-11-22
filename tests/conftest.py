"""Shared test fixtures.

pytest loads this file automatically. A *fixture* is a function that prepares something
a test needs. A test asks for one simply by naming it as a parameter, and pytest runs
the fixture and passes in the result. For example, ``def test_x(client):`` receives a
ready-to-use HTTP client.

Every test gets its own fresh database file, so tests never depend on each other or on
the order they run in.

How the suite is organised:

* ``test_<module>.py`` files test one module's functions directly (unit tests: fast and
  precise about one piece of logic).
* ``test_*_api.py`` files and ``test_cdns.py`` / ``test_steering.py`` send real HTTP
  requests to the app (integration tests: they check the pieces work together, including
  validation, authentication and status codes).
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import db
from app.main import create_app
from app.probes.models import Probe

# Headers that authenticate as an admin. The value matches the token the app falls back
# to when none is configured (see app/config.py).
ADMIN = {"X-Admin-Token": "changeme"}

# The type of the ``make_cdn`` fixture: a function that creates a CDN and returns it.
MakeCdn = Callable[..., dict[str, Any]]

# The type of the ``insert_probe`` fixture: a function that stores one probe.
InsertProbe = Callable[..., None]


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the app at an empty database file inside this test's temporary directory.

    Args:
        tmp_path: A temporary directory that pytest creates for this test (built-in
            fixture).
        monkeypatch: Lets the test change environment variables; pytest undoes the
            changes when the test ends (built-in fixture).

    Yields:
        The path of the database file. It does not exist until something connects.
        When the test ends, every pooled connection is closed.
    """
    path = tmp_path / "test.db"
    monkeypatch.setenv("EDGEROUTE_DB_PATH", str(path))
    yield path
    db.dispose_engines()


@pytest.fixture()
def client(db_path: Path) -> Iterator[TestClient]:
    """Provide an HTTP client for the app, backed by a fresh database file.

    ``TestClient`` calls the app directly in memory, without starting a web server, so
    tests are fast and need no network.

    Args:
        db_path: The fresh database file (fixture above).

    Yields:
        A client whose requests go to a newly created app.
    """
    # Using the client as a context manager runs the app's start-up code, which creates
    # the tables.
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def session(db_path: Path) -> Iterator[Session]:
    """Provide a session on a fresh database whose schema is fully migrated.

    Unit tests use it to call repository and service functions directly, without HTTP.

    Args:
        db_path: The fresh database file (fixture above).

    Yields:
        An open session. It is closed when the test ends; uncommitted changes are
        discarded.
    """
    db.migrate()
    with Session(db.get_engine()) as test_session:
        yield test_session


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    """Provide the headers that authenticate a request as an admin.

    Returns:
        A dictionary with the ``X-Admin-Token`` header.
    """
    return ADMIN


@pytest.fixture()
def make_cdn(client: TestClient, admin_headers: dict[str, str]) -> MakeCdn:
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
        **extra: Any,
    ) -> dict[str, Any]:
        """Register one CDN and fail the test straight away if that does not work.

        Args:
            name: The CDN's unique name.
            weight: Its share of traffic, from 0 to 100.
            enabled: Whether it may receive traffic.
            base_url: The root URL its assets are served from.
            **extra: Any other field to send, e.g. ``cost_per_gb_cents=4``.

        Returns:
            The created CDN, as returned by the API.
        """
        payload = {"name": name, "base_url": base_url, "weight": weight, "enabled": enabled}
        response = client.post("/api/v1/cdns", json=payload | extra, headers=admin_headers)
        # The second part of the assert is the message pytest shows if it fails.
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture()
def insert_probe(session: Session) -> InsertProbe:
    """Provide a function that stores one probe directly in the database.

    Health tests use it to set up exactly the probes they need, without going through
    the import.

    Args:
        session: Session on the fresh database (fixture above).

    Returns:
        A function that stores one probe.
    """

    def _insert(
        provider: str = "aurora",
        region: str = "eu-west",
        status_code: int = 200,
        ttfb_ms: float = 120.0,
        observed_at: str = "2026-11-17T08:00:00",
    ) -> None:
        """Store one probe and commit it.

        Args:
            provider: CDN name.
            region: Region the probe ran in.
            status_code: HTTP status the probe received.
            ttfb_ms: Time to first byte, in milliseconds.
            observed_at: When the probe ran, ISO 8601.
        """
        session.add(
            Probe(
                observed_at=observed_at,
                provider=provider,
                region=region,
                status_code=status_code,
                ttfb_ms=ttfb_ms,
            )
        )
        session.commit()

    return _insert

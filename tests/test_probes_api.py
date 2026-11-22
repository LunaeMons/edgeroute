"""Tests for the probe endpoints: ``POST /api/v1/probes/import`` and ``GET .../health/{region}``.

The parsing and validation rules are tested in detail in ``test_ingest.py`` and the
statistics in ``test_health.py``. These tests check the HTTP layer: uploads, status
codes, response shapes, and that an import is visible in the health report.
Authentication is tested in ``test_auth.py``.
"""

import pytest
from fastapi.testclient import TestClient

IMPORT = "/api/v1/probes/import"

CSV = (
    "timestamp,cdn_name,region,status,ttfb\n"
    "2026-11-17 08:00:00,aurora,eu-west,200,120ms\n"
    "2026-11-17 08:01:00,aurora,eu-west,500,120ms\n"
)


def test_import_endpoint(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Uploading a CSV stores its probes, and the health report reflects them.

    One of the two probes is a 500, so the error rate for aurora must be 50%.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    # ``files=`` sends a multipart upload: (file name, content, content type).
    response = client.post(
        IMPORT, files={"file": ("probes.csv", CSV, "text/csv")}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json() == {"total": 2, "imported": 2, "rejected": 0, "errors": []}
    report = client.get("/api/v1/probes/health/eu-west").json()
    assert report == {
        "region": "eu-west",
        "window": 50,
        "providers": {"aurora": {"samples": 2, "error_rate": 0.5, "p95_ttfb_ms": 120.0}},
    }


def test_import_reports_rejected_rows(client: TestClient, admin_headers: dict[str, str]) -> None:
    """The response lists each rejected row with its line number and the reason.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    content = CSV + "2026-11-17 08:02:00,aurora,,200,120ms\n"

    response = client.post(
        IMPORT, files={"file": ("probes.csv", content, "text/csv")}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 3,
        "imported": 2,
        "rejected": 1,
        "errors": [{"line": 3, "reason": "Missing required fields."}],
    }


def test_import_rejects_a_file_that_is_not_utf8_text(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """Binary content (here, bytes that are not valid UTF-8) is refused with 400.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.post(
        IMPORT,
        files={"file": ("probes.csv", b"\xff\xfe\x00binary", "text/csv")},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File must be UTF-8 text."}


def test_import_without_a_file_returns_422(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """A request with no ``file`` field is refused with 422 naming the field.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    response = client.post(IMPORT, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_health_for_a_region_without_probes_is_empty(client: TestClient) -> None:
    """A region with no probes answers 200 with no providers.

    Args:
        client: Test client with a fresh database.
    """
    response = client.get("/api/v1/probes/health/eu-north")

    assert response.status_code == 200
    assert response.json() == {"region": "eu-north", "window": 50, "providers": {}}


def test_health_uses_the_configured_window(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``EDGEROUTE_PROBE_WINDOW`` sets how many recent probes count, and is reported back.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
        monkeypatch: Sets the window for this test only.
    """
    client.post(IMPORT, files={"file": ("probes.csv", CSV, "text/csv")}, headers=admin_headers)
    monkeypatch.setenv("EDGEROUTE_PROBE_WINDOW", "1")

    report = client.get("/api/v1/probes/health/eu-west").json()

    assert report["window"] == 1
    # Only the newest probe (the 500 at 08:01) counts.
    assert report["providers"]["aurora"] == {"samples": 1, "error_rate": 1.0, "p95_ttfb_ms": 120.0}

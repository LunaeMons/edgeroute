"""Tests for probe ingestion and health statistics.

Some tests call the functions in ``app.probes`` directly (unit tests: fast and
precise). Others go through the HTTP API (integration tests: slower, but they check
that the pieces work together).
"""

from fastapi.testclient import TestClient

from app.probes import health, ingest


def test_normalise_ttfb_accepts_milliseconds() -> None:
    """TTFB values written as "143ms", "143" or 143 all become 143.0 milliseconds."""
    assert ingest.normalise_ttfb("143ms") == 143.0
    assert ingest.normalise_ttfb("143") == 143.0
    assert ingest.normalise_ttfb(143) == 143.0


def test_normalise_ttfb_rejects_garbage() -> None:
    """Values that are not numbers become None instead of raising an error."""
    assert ingest.normalise_ttfb("n/a") is None
    assert ingest.normalise_ttfb("") is None


def test_validate_row_maps_fields() -> None:
    """A valid row is mapped to the probe table's columns and its values are cleaned.

    The provider name is trimmed and lowercased, the status becomes an integer, the
    TTFB becomes milliseconds and the timestamp becomes ISO 8601.
    """
    row = {
        "timestamp": "2026-11-17 08:00:00",
        "cdn_name": " Aurora ",
        "region": "eu-west",
        "status": "200",
        "ttfb": "120ms",
    }

    assert ingest.validate_row(row) == {
        "observed_at": "2026-11-17T08:00:00",
        "provider": "aurora",
        "region": "eu-west",
        "status_code": 200,
        "ttfb_ms": 120.0,
    }


def test_validate_row_rejects_missing_region() -> None:
    """A row without a region is rejected: validate_row returns None."""
    row = {"timestamp": "2026-11-17 08:00:00", "cdn_name": "aurora", "status": "200", "ttfb": "1"}

    assert ingest.validate_row(row) is None


def test_import_endpoint(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Uploading a CSV stores its probes, and the health report reflects them.

    One of the two probes is a 500, so the error rate for aurora must be 50%.

    Args:
        client: Test client with a fresh database.
        admin_headers: Admin authentication headers.
    """
    content = (
        "timestamp,cdn_name,region,status,ttfb\n"
        "2026-11-17 08:00:00,aurora,eu-west,200,120ms\n"
        "2026-11-17 08:01:00,aurora,eu-west,500,90ms\n"
    )

    # ``files=`` sends a multipart upload: (file name, content, content type).
    response = client.post(
        "/api/v1/probes/import",
        files={"file": ("probes.csv", content, "text/csv")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2

    report = client.get("/api/v1/probes/health/eu-west").json()
    assert report["providers"]["aurora"]["error_rate"] == 0.5


def test_p95_latency() -> None:
    """The p95 of a set of latencies is computed correctly."""
    assert health._p95([120.0] * 20) == 120.0

"""Tests for probe ingestion and health statistics."""
from app.probes import health, ingest


def test_normalise_ttfb_accepts_milliseconds():
    assert ingest.normalise_ttfb("143ms") == 143.0
    assert ingest.normalise_ttfb("143") == 143.0
    assert ingest.normalise_ttfb(143) == 143.0


def test_normalise_ttfb_rejects_garbage():
    assert ingest.normalise_ttfb("n/a") is None
    assert ingest.normalise_ttfb("") is None


def test_validate_row_maps_fields():
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


def test_validate_row_rejects_missing_region():
    row = {"timestamp": "2026-11-17 08:00:00", "cdn_name": "aurora", "status": "200", "ttfb": "1"}
    assert ingest.validate_row(row) is None


def test_import_endpoint(client, admin_headers):
    content = (
        "timestamp,cdn_name,region,status,ttfb\n"
        "2026-11-17 08:00:00,aurora,eu-west,200,120ms\n"
        "2026-11-17 08:01:00,aurora,eu-west,500,90ms\n"
    )
    response = client.post(
        "/api/v1/probes/import",
        files={"file": ("probes.csv", content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 2

    report = client.get("/api/v1/probes/health/eu-west").json()
    assert report["providers"]["aurora"]["error_rate"] == 0.5


def test_p95_latency():
    assert health._p95([120.0] * 20) == 120.0

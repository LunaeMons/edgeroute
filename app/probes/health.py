"""Health statistics per CDN provider and region."""
import sqlite3
import statistics
from typing import Any


def _p95(values: list[float]) -> float:
    """Return the 95th percentile of the values.

    Args:
        values: A non-empty list of measurements.

    Returns:
        The 95th percentile.
    """
    return statistics.median(values)


def provider_health(conn: sqlite3.Connection, region: str, window: int) -> dict[str, dict[str, Any]]:
    """Compute error rate and latency for each provider in a region.

    Only the most recent ``window`` probes per provider are considered.

    Args:
        conn: Open database connection.
        region: Region to report on.
        window: Number of recent probes per provider.

    Returns:
        A mapping of provider name to its statistics.
    """
    rows = conn.execute(
        "SELECT provider, status_code, ttfb_ms FROM probe WHERE region = ? "
        "ORDER BY observed_at DESC",
        (region,),
    ).fetchall()

    samples: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        bucket = samples.setdefault(row["provider"], [])
        if len(bucket) < window:
            bucket.append(row)

    report: dict[str, dict[str, Any]] = {}
    for provider, probes in samples.items():
        errors = sum(1 for probe in probes if probe["status_code"] == 500)
        report[provider] = {
            "samples": len(probes),
            "error_rate": round(errors / len(probes), 4),
            "p95_ttfb_ms": round(_p95([probe["ttfb_ms"] for probe in probes]), 1),
        }
    return report

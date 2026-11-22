"""Health statistics per CDN provider and region.

For each CDN in a region, health is summarised by two numbers computed over its most
recent probes:

* the **error rate**: the share of probes that failed, from 0.0 to 1.0;
* the **p95 TTFB**: the time to first byte that 95% of probes beat. It shows what the
  slowest viewers experience, which an average hides.
"""

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

    Only the most recent ``window`` probes per provider are considered, so the figures
    reflect current behaviour rather than all of history.

    Args:
        conn: Open database connection.
        region: Region to report on, e.g. ``"eu-west"``.
        window: Number of recent probes per provider.

    Returns:
        A mapping of provider name to its statistics: ``samples`` (probes used),
        ``error_rate`` (0.0 to 1.0) and ``p95_ttfb_ms``. A provider with no probes in
        the region is absent.
    """
    # Newest probes first, so the first ``window`` rows per provider are the latest ones.
    rows = conn.execute(
        "SELECT provider, status_code, ttfb_ms FROM probe WHERE region = ? "
        "ORDER BY observed_at DESC",
        (region,),
    ).fetchall()

    # Group the rows by provider, keeping at most ``window`` probes for each.
    # ``setdefault`` returns the provider's list, creating an empty one the first time.
    samples: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        bucket = samples.setdefault(row["provider"], [])
        if len(bucket) < window:
            bucket.append(row)

    report: dict[str, dict[str, Any]] = {}
    for provider, probes in samples.items():
        # Count the probes that failed.
        errors = sum(1 for probe in probes if probe["status_code"] == 500)
        report[provider] = {
            "samples": len(probes),
            "error_rate": round(errors / len(probes), 4),
            "p95_ttfb_ms": round(_p95([probe["ttfb_ms"] for probe in probes]), 1),
        }
    return report

"""Unit tests for the health statistics (``app.probes.health``).

Probes are inserted straight into the database with the ``insert_probe`` fixture, so
each test controls exactly which measurements exist.
"""

from sqlalchemy.orm import Session

from app.probes import health
from tests.conftest import InsertProbe


def test_region_without_probes_has_an_empty_report(session: Session) -> None:
    """A region with no probes reports no providers, rather than failing.

    Args:
        session: Session on a fresh, migrated database.
    """
    assert health.provider_health(session, "eu-west", window=50) == {}


def test_report_contains_samples_error_rate_and_p95(
    session: Session, insert_probe: InsertProbe
) -> None:
    """A provider's entry holds exactly three figures: samples, error rate and p95 TTFB.

    One probe out of four failed with a 500, so the error rate is 0.25.

    Args:
        session: Session on a fresh, migrated database.
        insert_probe: Stores one probe.
    """
    for minute, status in enumerate([200, 200, 500, 200]):
        insert_probe(status_code=status, observed_at=f"2026-11-17T08:0{minute}:00")

    report = health.provider_health(session, "eu-west", window=50)

    assert report == {"aurora": {"samples": 4, "error_rate": 0.25, "p95_ttfb_ms": 120.0}}


def test_error_rate_is_rounded_to_four_decimals(
    session: Session, insert_probe: InsertProbe
) -> None:
    """One failure in three probes is reported as 0.3333, not 0.333333...

    Args:
        session: Session on a fresh, migrated database.
        insert_probe: Stores one probe.
    """
    for minute, status in enumerate([500, 200, 200]):
        insert_probe(status_code=status, observed_at=f"2026-11-17T08:0{minute}:00")

    report = health.provider_health(session, "eu-west", window=50)

    assert report["aurora"]["error_rate"] == 0.3333


def test_only_the_most_recent_probes_count(session: Session, insert_probe: InsertProbe) -> None:
    """With a window of 3, only the 3 newest probes count, whatever the insertion order.

    The two oldest probes are failures. If they were counted, the error rate would not
    be zero. They are inserted last, to prove the window follows ``observed_at`` and
    not the insertion order.

    Args:
        session: Session on a fresh, migrated database.
        insert_probe: Stores one probe.
    """
    insert_probe(status_code=200, observed_at="2026-11-17T08:04:00")
    insert_probe(status_code=200, observed_at="2026-11-17T08:03:00")
    insert_probe(status_code=200, observed_at="2026-11-17T08:02:00")
    insert_probe(status_code=500, observed_at="2026-11-17T08:01:00")
    insert_probe(status_code=500, observed_at="2026-11-17T08:00:00")

    report = health.provider_health(session, "eu-west", window=3)

    assert report["aurora"]["samples"] == 3
    assert report["aurora"]["error_rate"] == 0.0


def test_each_provider_has_its_own_window(session: Session, insert_probe: InsertProbe) -> None:
    """The window applies per provider: a busy provider does not crowd out a quiet one.

    Args:
        session: Session on a fresh, migrated database.
        insert_probe: Stores one probe.
    """
    for minute in range(5):
        insert_probe(provider="aurora", observed_at=f"2026-11-17T08:0{minute}:00")
    insert_probe(provider="kestrel", observed_at="2026-11-17T07:00:00")

    report = health.provider_health(session, "eu-west", window=2)

    assert {name: stats["samples"] for name, stats in report.items()} == {"aurora": 2, "kestrel": 1}


def test_report_only_covers_the_requested_region(
    session: Session, insert_probe: InsertProbe
) -> None:
    """Probes from other regions are ignored.

    Args:
        session: Session on a fresh, migrated database.
        insert_probe: Stores one probe.
    """
    insert_probe(provider="aurora", region="eu-west")
    insert_probe(provider="meridian", region="eu-south", status_code=500)

    report = health.provider_health(session, "eu-west", window=50)

    assert list(report) == ["aurora"]
    assert report["aurora"]["error_rate"] == 0.0


def test_p95_latency() -> None:
    """The p95 of a set of latencies is computed correctly."""
    assert health._p95([120.0] * 20) == 120.0
    assert health._p95([80.0]) == 80.0

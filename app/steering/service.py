"""Steering logic: decide which CDN serves a viewer."""
import random
import sqlite3
from typing import Any


def eligible_cdns(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return the CDN providers that may receive traffic.

    Args:
        conn: Open database connection.

    Returns:
        Enabled providers with a positive weight.
    """
    rows = conn.execute("SELECT id, name, base_url, weight, enabled FROM cdn").fetchall()
    return [dict(row) for row in rows if row["enabled"] and row["weight"] > 0]


def choose_cdn(
    conn: sqlite3.Connection, region: str, session_id: str | None = None
) -> dict[str, Any] | None:
    """Pick a CDN for a viewer using the configured weights.

    Args:
        conn: Open database connection.
        region: The viewer's region, e.g. "eu-west".
        session_id: The player session, if known.

    Returns:
        The chosen provider, or None if no provider is eligible.
    """
    candidates = eligible_cdns(conn)
    if not candidates:
        return None
    weights = [cdn["weight"] for cdn in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]  # noqa: S311

"""Database access for CDN providers."""
import sqlite3
from typing import Any

from app.cdns.schemas import CdnCreate, CdnUpdate

_COLUMNS = "id, name, base_url, weight, enabled, cost_per_gb_cents, created_at"


def list_cdns(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every CDN provider, ordered by name.

    Args:
        conn: Open database connection.

    Returns:
        The providers as dictionaries.
    """
    rows = conn.execute(f"SELECT {_COLUMNS} FROM cdn ORDER BY name").fetchall()  # noqa: S608
    return [dict(row) for row in rows]


def get_cdn(conn: sqlite3.Connection, cdn_id: int) -> dict[str, Any] | None:
    """Return one CDN provider.

    Args:
        conn: Open database connection.
        cdn_id: The provider's ID.

    Returns:
        The provider, or None if it does not exist.
    """
    row = conn.execute(f"SELECT {_COLUMNS} FROM cdn WHERE id = ?", (cdn_id,)).fetchone()  # noqa: S608
    return dict(row) if row else None


def create_cdn(conn: sqlite3.Connection, payload: CdnCreate) -> dict[str, Any]:
    """Insert a CDN provider.

    Args:
        conn: Open database connection.
        payload: Validated provider data.

    Returns:
        The stored provider.

    Raises:
        ValueError: If a provider with the same name exists.
    """
    try:
        cursor = conn.execute(
            "INSERT INTO cdn (name, base_url, weight, enabled, cost_per_gb_cents) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                payload.name,
                str(payload.base_url),
                payload.weight,
                "true" if payload.enabled else "false",
                payload.cost_per_gb_cents,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"CDN '{payload.name}' already exists.") from exc
    return get_cdn(conn, cursor.lastrowid)  # type: ignore[arg-type,return-value]


def update_cdn(
    conn: sqlite3.Connection, cdn_id: int, payload: CdnUpdate
) -> dict[str, Any] | None:
    """Apply a partial update to a CDN provider.

    Args:
        conn: Open database connection.
        cdn_id: The provider's ID.
        payload: Fields to change.

    Returns:
        The updated provider, or None if it does not exist.
    """
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return get_cdn(conn, cdn_id)
    if "enabled" in changes:
        changes["enabled"] = "true" if changes["enabled"] else "false"
    if "base_url" in changes:
        changes["base_url"] = str(changes["base_url"])
    assignments = ", ".join(f"{column} = ?" for column in changes)
    conn.execute(
        f"UPDATE cdn SET {assignments} WHERE id = ?",  # noqa: S608
        (*changes.values(), cdn_id),
    )
    return get_cdn(conn, cdn_id)


def delete_cdn(conn: sqlite3.Connection, cdn_id: int) -> bool:
    """Delete a CDN provider.

    Args:
        conn: Open database connection.
        cdn_id: The provider's ID.

    Returns:
        True if a row was deleted.
    """
    cursor = conn.execute("DELETE FROM cdn WHERE id = ?", (cdn_id,))
    return cursor.rowcount > 0

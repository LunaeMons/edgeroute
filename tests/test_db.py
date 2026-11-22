"""Tests for the SQLite helpers (``app.db``)."""

import sqlite3
from pathlib import Path

import pytest

from app import db


def _table_names(path: Path) -> set[str]:
    """Return the names of the tables in a database file.

    Args:
        path: The database file.

    Returns:
        The table names, excluding SQLite's internal tables.
    """
    with sqlite3.connect(path) as raw:
        rows = raw.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {name for (name,) in rows}


def _count_cdns(path: Path) -> int:
    """Count the rows in the ``cdn`` table, using a separate connection.

    A separate connection only sees committed data, which is what the commit and
    rollback tests need to check.

    Args:
        path: The database file.

    Returns:
        The number of CDN rows.
    """
    with sqlite3.connect(path) as raw:
        return raw.execute("SELECT COUNT(*) FROM cdn").fetchone()[0]


def _insert_cdn(conn: sqlite3.Connection) -> None:
    """Insert one CDN row without committing it.

    Args:
        conn: Open connection.
    """
    conn.execute("INSERT INTO cdn (name, base_url) VALUES ('aurora', 'https://a.example')")


def test_init_db_creates_the_tables(db_path: Path) -> None:
    """Initialising an empty database creates the ``cdn`` and ``probe`` tables.

    Args:
        db_path: Path of a database file that does not exist yet.
    """
    db.init_db()

    assert _table_names(db_path) == {"cdn", "probe"}


def test_init_db_can_run_again_without_losing_data(db_path: Path) -> None:
    """Running the schema a second time, as every start-up does, keeps existing rows.

    Args:
        db_path: Path of a fresh database file.
    """
    db.init_db()
    with db.connect() as conn:
        _insert_cdn(conn)

    db.init_db()

    assert _count_cdns(db_path) == 1


def test_connect_returns_rows_readable_by_column_name(db_path: Path) -> None:
    """Rows from :func:`db.connect` can be read like dictionaries: ``row["name"]``.

    Args:
        db_path: Path of a fresh database file.
    """
    db.init_db()
    conn = db.connect()
    _insert_cdn(conn)

    row = conn.execute("SELECT name, weight, enabled FROM cdn").fetchone()

    assert (row["name"], row["weight"], row["enabled"]) == ("aurora", 1, "true")
    conn.close()


def test_get_conn_commits_when_the_request_succeeds(db_path: Path) -> None:
    """Changes made during a successful request are saved.

    FastAPI drives the dependency like this: ``next()`` runs it up to ``yield`` and
    hands over the connection; the second ``next()`` runs the rest after the endpoint
    returns, which ends the generator with ``StopIteration``.

    Args:
        db_path: Path of a fresh database file.
    """
    db.init_db()
    dependency = db.get_conn()
    conn = next(dependency)
    _insert_cdn(conn)

    with pytest.raises(StopIteration):
        next(dependency)

    assert _count_cdns(db_path) == 1


def test_get_conn_discards_changes_and_closes_when_the_request_fails(db_path: Path) -> None:
    """Changes made during a failed request are not saved, and the connection is closed.

    ``throw()`` is how FastAPI tells the dependency that the endpoint raised.

    Args:
        db_path: Path of a fresh database file.
    """
    db.init_db()
    dependency = db.get_conn()
    conn = next(dependency)
    _insert_cdn(conn)

    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError("endpoint failed"))

    assert _count_cdns(db_path) == 0
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")

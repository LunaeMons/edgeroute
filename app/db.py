"""SQLite access helpers."""
import sqlite3
from collections.abc import Iterator

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS cdn (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 1,
    enabled TEXT NOT NULL DEFAULT 'true',
    cost_per_gb_cents INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS probe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,
    provider TEXT NOT NULL,
    region TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    ttfb_ms REAL NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    """Open a connection to the configured database.

    Returns:
        A connection whose rows behave like dictionaries.
    """
    conn = sqlite3.connect(get_settings().db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_conn() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency that yields a connection and commits on success.

    Yields:
        An open database connection.
    """
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

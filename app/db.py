"""SQLite access helpers.

EdgeRoute stores its data in a single SQLite file (see ADR 0001). There are two tables:

* ``cdn``: one row per CDN provider, with its base URL, steering weight and status.
* ``probe``: one row per measurement taken by a probe agent: when, which CDN, from
  which region, the HTTP status it got and how long the first byte took (TTFB).

Endpoints get a connection through the :func:`get_conn` dependency; scripts call
:func:`connect` directly.
"""

import sqlite3
from collections.abc import Iterator

from app.config import get_settings

# ``CREATE TABLE IF NOT EXISTS`` makes the schema safe to apply on every start-up: it
# creates missing tables and leaves existing ones, and their data, untouched.
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

    ``check_same_thread=False`` lets FastAPI use the connection from the worker thread
    that serves the request, which is not always the thread that opened it.

    Returns:
        A connection whose rows can be read by column name, like a dictionary
        (``row["name"]``).
    """
    conn = sqlite3.connect(get_settings().db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    # Used as a context manager, a connection commits when the block succeeds and
    # rolls back if it raises.
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_conn() -> Iterator[sqlite3.Connection]:
    """Provide one database connection per request (a FastAPI dependency).

    An endpoint asks for a connection by declaring a parameter
    ``conn: sqlite3.Connection = Depends(get_conn)``. FastAPI runs this function up to
    the ``yield``, passes the connection to the endpoint, and runs the rest once the
    endpoint has returned.

    Yields:
        An open database connection. Changes are committed if the endpoint succeeds,
        and the connection is always closed afterwards.
    """
    conn = connect()
    try:
        yield conn
        # Only reached when the endpoint did not raise: keep its changes.
        conn.commit()
    finally:
        # Runs whether the endpoint succeeded or failed.
        conn.close()

"""Database access: the SQLAlchemy engine, sessions, and schema migrations.

EdgeRoute talks to its database through SQLAlchemy, the standard Python ORM
(object-relational mapper). Tables are described once, as Python classes (the *models*,
in each feature's ``models.py``). Code then works with objects (``cdn.weight = 30``)
instead of writing SQL by hand, and the same code runs on SQLite today and on
PostgreSQL later (see ADR 0002).

Three ideas to know:

* The **engine** knows how to reach the database. There is one per database URL.
* A **session** is a unit of work: it tracks the objects you load, add or change, and
  writes them all in one transaction when you commit. Each HTTP request gets its own
  session from :func:`get_session`.
* **Migrations** (Alembic, in ``migrations/``) create and change the tables. The models
  say what the schema should be; a migration is the script that gets an existing
  database there without losing its data.
"""

from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings

# The project root, where alembic.ini lives.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Base(DeclarativeBase):
    """Parent class of every model: it collects their tables into one schema.

    Alembic compares ``Base.metadata`` (every table the models define) with the
    database to tell whether a migration is missing.
    """


def database_url() -> str:
    """Build the SQLAlchemy URL of the configured database.

    Returns:
        A URL such as ``sqlite:///edgeroute.db``.
    """
    return f"sqlite:///{get_settings().db_path}"


# One engine per database URL, created on first use and then reused, so requests share
# a pool of open connections instead of reconnecting every time.
_engines: dict[str, Engine] = {}


def get_engine() -> Engine:
    """Return the engine for the currently configured database.

    The settings are read on every call, so tests that point ``EDGEROUTE_DB_PATH`` at a
    temporary file get an engine for that file.

    Returns:
        The engine, created on the first call for this database.
    """
    url = database_url()
    if url not in _engines:
        # SQLite ties a connection to the thread that opened it. FastAPI may serve a
        # request on another worker thread, so allow that.
        _engines[url] = create_engine(url, connect_args={"check_same_thread": False})
    return _engines[url]


def dispose_engines() -> None:
    """Close every pooled connection and forget the engines.

    Called when the application shuts down, and by tests when they finish with a
    database.
    """
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


def alembic_config() -> Config:
    """Load the Alembic configuration, so migrations can be run from Python.

    Returns:
        The configuration from ``alembic.ini``, which works from any working directory.
    """
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def migrate() -> None:
    """Bring the database schema up to date by applying any pending migrations.

    Safe to run on every start-up: migrations that were already applied are skipped
    (Alembic records the current revision in the ``alembic_version`` table).
    """
    command.upgrade(alembic_config(), "head")


def get_session() -> Iterator[Session]:
    """Provide one database session per request (a FastAPI dependency).

    An endpoint asks for a session by declaring a parameter
    ``session: Session = Depends(get_session)``. FastAPI runs this function up to the
    ``yield``, passes the session to the endpoint, and runs the rest once the endpoint
    has finished.

    Yields:
        An open session. Its changes are committed if the endpoint succeeds and rolled
        back if it raises; the session is always closed afterwards.
    """
    with Session(get_engine()) as session:
        try:
            yield session
            # Only reached when the endpoint did not raise: save its changes.
            session.commit()
        except Exception:
            # Undo everything the failed request changed, then let the error continue.
            session.rollback()
            raise

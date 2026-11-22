"""Tests for the database layer (``app.db``) and the migrations in ``migrations/``."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, func, inspect, select

from app import db
from app.cdns.models import Cdn


def _table_names() -> set[str]:
    """Return the names of the tables in the configured database.

    Returns:
        The table names.
    """
    return set(inspect(db.get_engine()).get_table_names())


def _count_cdns() -> int:
    """Count the committed rows in the ``cdn`` table, using a new connection.

    A new connection only sees committed data, which is what the commit and rollback
    tests need to check.

    Returns:
        The number of CDN rows.
    """
    with db.get_engine().connect() as connection:
        return connection.scalar(select(func.count()).select_from(Cdn))


def test_database_url_points_at_the_configured_file(db_path: Path) -> None:
    """The SQLAlchemy URL is built from ``EDGEROUTE_DB_PATH``.

    Args:
        db_path: Path of a fresh database file.
    """
    assert db.database_url() == f"sqlite:///{db_path}"


def test_migrate_creates_the_tables(db_path: Path) -> None:
    """Migrating an empty database creates the tables and records the revision.

    Args:
        db_path: Path of a database file that does not exist yet.
    """
    db.migrate()

    assert _table_names() == {"alembic_version", "cdn", "probe"}
    with db.get_engine().connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == "0001"


def test_migrate_can_run_again_without_losing_data(db_path: Path) -> None:
    """Migrating an up-to-date database, as every start-up does, changes nothing.

    Args:
        db_path: Path of a fresh database file.
    """
    db.migrate()
    with db.get_engine().begin() as connection:
        connection.execute(
            Cdn.__table__.insert().values(name="aurora", base_url="https://a.example")
        )

    db.migrate()

    assert _count_cdns() == 1


def test_models_and_migrations_describe_the_same_schema(db_path: Path) -> None:
    """After all migrations run, the database matches the models exactly.

    This fails when someone changes a model but forgets the migration (or the other way
    round). Alembic's autogenerate compares the two and lists every difference; the
    list must be empty.

    Args:
        db_path: Path of a fresh database file.
    """
    db.migrate()

    with db.get_engine().connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), db.Base.metadata)

    assert differences == []


def _schema(engine: Engine) -> dict[str, dict[str, object]]:
    """Describe every table of a database: columns, primary key, unique constraints, indexes.

    Args:
        engine: Engine of the database to describe.

    Returns:
        A comparable description per table, ignoring Alembic's own bookkeeping table.
    """
    inspector = inspect(engine)
    return {
        table: {
            "columns": [
                (c["name"], str(c["type"]), c["nullable"]) for c in inspector.get_columns(table)
            ],
            "primary_key": inspector.get_pk_constraint(table)["constrained_columns"],
            "unique": sorted(u["column_names"] for u in inspector.get_unique_constraints(table)),
            "indexes": sorted((i["name"], i["column_names"]) for i in inspector.get_indexes(table)),
        }
        for table in inspector.get_table_names()
        if table != "alembic_version"
    }


def test_models_create_the_same_tables_as_the_migrations(db_path: Path, tmp_path: Path) -> None:
    """A database built from the models is identical to one built by the migrations.

    This complements the autogenerate check above, which cannot see every kind of
    difference on SQLite (unnamed unique constraints, for example). Here both databases
    are built for real and their tables compared column by column.

    Args:
        db_path: Path of a fresh database file, built by the migrations.
        tmp_path: This test's temporary directory, for the database built from the models.
    """
    db.migrate()
    from_models = create_engine(f"sqlite:///{tmp_path / 'from_models.db'}")
    db.Base.metadata.create_all(from_models)

    assert _schema(from_models) == _schema(db.get_engine())
    from_models.dispose()


def test_every_migration_can_be_undone(db_path: Path) -> None:
    """Downgrading to the start removes the tables, and upgrading again rebuilds them.

    A migration that cannot be undone makes a bad release much harder to roll back.

    Args:
        db_path: Path of a fresh database file.
    """
    db.migrate()

    command.downgrade(db.alembic_config(), "base")
    assert _table_names() == {"alembic_version"}

    db.migrate()
    assert _table_names() == {"alembic_version", "cdn", "probe"}


def test_get_engine_reuses_one_engine_per_database(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same database always gets the same engine; another database gets its own.

    Args:
        db_path: Path of a fresh database file.
        tmp_path: This test's temporary directory.
        monkeypatch: Points the app at a second database.
    """
    first = db.get_engine()
    assert db.get_engine() is first

    monkeypatch.setenv("EDGEROUTE_DB_PATH", str(tmp_path / "other.db"))

    assert db.get_engine() is not first


def test_dispose_engines_forgets_the_engines(db_path: Path) -> None:
    """After disposal, the next call creates a fresh engine.

    Args:
        db_path: Path of a fresh database file.
    """
    first = db.get_engine()

    db.dispose_engines()

    assert db.get_engine() is not first


def test_get_session_commits_when_the_request_succeeds(db_path: Path) -> None:
    """Changes made during a successful request are saved.

    FastAPI drives the dependency like this: ``next()`` runs it up to ``yield`` and
    hands over the session; the second ``next()`` runs the rest after the endpoint
    returns, which ends the generator with ``StopIteration``.

    Args:
        db_path: Path of a fresh database file.
    """
    db.migrate()
    dependency = db.get_session()
    session = next(dependency)
    session.add(Cdn(name="aurora", base_url="https://a.example"))

    with pytest.raises(StopIteration):
        next(dependency)

    assert _count_cdns() == 1


def test_get_session_rolls_back_when_the_request_fails(db_path: Path) -> None:
    """Changes made during a failed request are discarded, and the error is passed on.

    ``throw()`` is how FastAPI tells the dependency that the endpoint raised.

    Args:
        db_path: Path of a fresh database file.
    """
    db.migrate()
    dependency = db.get_session()
    session = next(dependency)
    session.add(Cdn(name="aurora", base_url="https://a.example"))
    session.flush()

    with pytest.raises(RuntimeError, match="endpoint failed"):
        dependency.throw(RuntimeError("endpoint failed"))

    assert _count_cdns() == 0
    assert not session.in_transaction()

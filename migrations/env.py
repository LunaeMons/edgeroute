"""Alembic environment: tells Alembic which database to migrate and what the models look like.

Alembic runs this file for every migration command. You rarely need to change it.
"""

from alembic import context

# Importing the model modules registers their tables on Base.metadata, which is what
# ``alembic revision --autogenerate`` compares the database against.
import app.cdns.models  # noqa: F401
import app.probes.models  # noqa: F401
from app import db

target_metadata = db.Base.metadata


def run_migrations_offline() -> None:
    """Write the migration SQL to the screen instead of running it (``alembic upgrade --sql``).

    Useful to review exactly what a migration will do to a production database.
    """
    context.configure(
        url=db.database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the configured database and apply the migrations."""
    with db.get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot alter most constraints in place. Batch mode makes Alembic
            # rebuild the table instead (copy, recreate, move the data back), so the
            # same migration works on SQLite and PostgreSQL.
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# 0002. SQLAlchemy ORM and Alembic migrations

- **Status:** Accepted
- **Date:** 2026-11-21
- **Ticket:** NWM-100

## Context

The first iteration used plain SQL through Python's `sqlite3` module (ADR 0001). Three problems
showed up as the code grew:

- SQL strings were spread across modules, and every new query was another chance to build SQL by
  formatting strings, which invites SQL injection.
- The schema was a `CREATE TABLE IF NOT EXISTS` script run at start-up. It can create tables but
  never change them, so any column added later (for example a probe ID) would need hand-written,
  untracked `ALTER TABLE` statements on every environment.
- Moving to PostgreSQL (see NWM-106) would mean rewriting every query.

## Options considered

1. **Keep plain SQL** and add a hand-rolled migration script. Small, but we would be inventing
   migration tracking ourselves.
2. **SQLAlchemy 2.0 ORM + Alembic.** The standard Python stack. Tables are declared once as typed
   models, queries are built in Python with parameters bound automatically, and Alembic
   versions every schema change. One more dependency to learn.
3. **SQLModel** (pydantic + SQLAlchemy in one class). Less code, but younger, and it mixes the API
   contract with the database schema in the same class.

## Decision

Option 2. Models live in each feature's `models.py`, API schemas stay separate in `schemas.py`,
and every schema change is an Alembic migration in `migrations/versions/`. The app applies
pending migrations at start-up (`app.db.migrate`).

## Consequences

- Schema changes are reviewed in pull requests like code, and every environment reaches the same
  schema by running the same migrations in order.
- A test (`test_models_and_migrations_describe_the_same_schema`) fails if a model changes without
  a matching migration.
- Switching to PostgreSQL is mostly a change of database URL, plus testing.
- Running migrations at start-up is fine for a single instance. With several instances starting
  at once, migrations should become a separate deployment step (see NWM-106).
- On SQLite, Alembic must rebuild a table to change its constraints. `migrations/env.py` enables
  batch mode, so generated migrations do this automatically.

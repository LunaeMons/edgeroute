# 0001. SQLite for the first iteration

- **Status:** Accepted. The data-access part (plain SQL) is superseded by
  [ADR 0002](0002-sqlalchemy-orm-and-alembic-migrations.md); SQLite itself still stands.
- **Date:** 2026-11-03
- **Ticket:** NWM-090

## Context

We need somewhere to store CDN configuration and probe measurements while we prove the steering
idea with operations. Volumes are small (a few CDNs, a few thousand probes a day) and there is one
instance of the service.

## Options considered

1. **PostgreSQL**: production-grade and multi-instance, but needs a server to run in every
   environment, including laptops and CI.
2. **SQLite**: a single file, zero setup, enough for one instance. It does not work for several
   instances writing at once.

## Decision

SQLite, accessed through plain SQL in small repository modules, so moving to PostgreSQL later
only touches those modules.

## Consequences

- Setup is trivial for developers and CI.
- We can only run one instance. Running several needs a different database (see NWM-106).
- The database file must live on persistent storage wherever the service runs.

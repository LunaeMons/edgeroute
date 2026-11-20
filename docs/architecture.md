# Architecture (current state)

EdgeRoute is a single FastAPI service with a SQLite database.

```mermaid
flowchart LR
    Player -->|GET /api/v1/steer| API[EdgeRoute API]
    Ops[Operations] -->|admin: CDNs, probe imports| API
    Agents[Probe agents] -.->|CSV / JSONL exports, uploaded by ops| Ops
    API --> DB[(SQLite)]
    Player -->|fetches stream| CDNs[aurora / meridian / kestrel]
```

## Modules

| Module | Responsibility |
|---|---|
| `app/main.py` | Application factory, router wiring, `/healthz` |
| `app/config.py` | Settings from environment variables |
| `app/db.py` | SQLite connection and schema |
| `app/auth.py` | Admin token check for write endpoints |
| `app/cdns/` | CRUD for CDN providers (name, base URL, weight, enabled, cost) |
| `app/steering/` | Picks a CDN for a viewer by weighted random choice |
| `app/probes/` | Imports probe exports, computes health statistics per CDN and region |

## Data model

- `cdn`: one row per provider. `weight` is its share of traffic relative to the others.
- `probe`: one row per probe measurement (time, provider, region, status, TTFB in ms).

## Known gaps

- Steering ignores probe health and the viewer's region (NWM-103).
- Probe ingestion is incomplete (NWM-102).
- No release process or production container setup yet (NWM-104).
- No user interface: operations use curl or the Swagger page at `/docs` (NWM-107).

# Quickstart

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs the right Python for you)
- Git
- Docker, for the container setup (optional for local development)

## Run it locally

```bash
git clone https://github.com/<you>/edgeroute.git   # your fork, see the README
cd edgeroute
make install                                  # creates .venv and installs dependencies
export EDGEROUTE_ADMIN_TOKEN=pick-a-local-secret
make seed                                     # creates the schema, loads data/cdns.json
make run
```

Open http://localhost:8080/docs to browse the API.

## Try it

Ask where a viewer in eu-west should play a stream from:

```bash
curl "http://localhost:8080/api/v1/steer?region=eu-west&asset=/live/nw1/master.m3u8"
```

Import a probe export (admin endpoints need the `X-Admin-Token` header):

```bash
curl -X POST http://localhost:8080/api/v1/probes/import \
  -H "X-Admin-Token: $EDGEROUTE_ADMIN_TOKEN" \
  -F "file=@data/probes_2026-11-17.csv"

curl http://localhost:8080/api/v1/probes/health/eu-west
```

## Run the tests

```bash
make test
```

## Run it in Docker

```bash
docker compose up --build
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `EDGEROUTE_ADMIN_TOKEN` | — | Secret for the admin endpoints (`X-Admin-Token` header) |
| `EDGEROUTE_DB_PATH` | `edgeroute.db` | SQLite database file |
| `EDGEROUTE_PROBE_WINDOW` | `50` | Recent probes per CDN and region used for health |

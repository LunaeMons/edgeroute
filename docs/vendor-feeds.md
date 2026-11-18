# Probe agent exports

Each region runs probe agents. Every few minutes, an agent requests a small test object from each
CDN and records what happened. The agents export their results in batches, which we upload to
`POST /api/v1/probes/import`.

There are two generations of agent. The v1 agent is being replaced by v2. During the migration
week (from 17 November 2026) both agents ran, and the v2 agent back-filled some results already
exported by v1.

## Fields (both versions)

| Field | Meaning |
|---|---|
| `timestamp` | When the probe ran (UTC) |
| `cdn` | Provider short name. Matches `name` in our CDN table, e.g. `aurora` |
| `region` | Region the agent runs in, e.g. `eu-west` |
| `status` | HTTP status code of the probe request. `0` means the probe timed out (no response within 5 s) |
| `ttfb` | Time to first byte |
| `probe_id` | Assigned by the probe scheduler. Unique per probe and the same in both agent versions |

## v1 agent: CSV

- File extension `.csv`, header row first.
- `timestamp` is `YYYY-MM-DD HH:MM:SS` in UTC, without an offset.
- `ttfb` is a string in milliseconds with a unit suffix, e.g. `143ms`. On timeout it is `5000ms`.

```
timestamp,cdn,region,status,ttfb,probe_id
2026-11-17 08:00:11,meridian,eu-south,200,240ms,pr-1af38d0923
```

## v2 agent: JSON Lines

- File extension `.jsonl`, one JSON object per line.
- `timestamp` is ISO 8601 with a `Z` suffix.
- `ttfb` is a number **in seconds**, e.g. `0.143`. On timeout it is `5.0`.
- `status` is an integer.

```
{"timestamp": "2026-11-17T08:30:41Z", "cdn": "aurora", "region": "eu-west", "status": 200, "ttfb": 0.143, "probe_id": "pr-0c1d2e3f4a"}
```

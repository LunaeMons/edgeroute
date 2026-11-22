# Contributing

How this team works. The goal is a `main` branch that is always releasable and a history that
explains itself.

## Branches

- `main` is the only long-lived branch. It must always pass CI.
- Create one branch per ticket from an up-to-date `main`:
  `feature/NWM-123-short-description` or `fix/NWM-123-short-description`.
- Keep branches short-lived. Rebase on `main` if it moves while you work.
- Delete the branch after it is merged.

## Commit messages

Format:

```
NWM-123 type(scope): imperative summary of the change

Optional body: why the change was needed and anything a reviewer
should know. Wrap at 72 characters.
```

- `type` is one of `feat`, `fix`, `test`, `docs`, `ci`, `build`, `refactor`, `chore`.
- `scope` is the area touched: `probes`, `steering`, `cdns`, `ci`, `docker`, ...
- The summary is in the imperative ("add", not "added"), at most 72 characters, with no full stop.
- One logical change per commit. A reviewer should be able to read the history like a changelog.

Examples:

```
NWM-102 fix(probes): read the provider from the cdn column
NWM-102 test(probes): cover JSONL imports and duplicate probes
NWM-101 ci: run tests on pull requests into main
```

The format is enforced by the `commit-msg` hook (see `scripts/check-commit-msg.sh` for the exact
rules).

## Code style: docstrings and comments

Code is read far more often than it is written, often by someone new to the codebase. Write
for that reader.

- **Every module, class and function has a docstring**, in the
  [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
  That includes tests, fixtures and private helpers.
  - A one-line summary in the imperative ("Return ...", "Reject ..."), ending with a full stop.
  - `Args:`, `Returns:` (or `Yields:`) and `Raises:` sections whenever they apply.
  - A class lists its fields under `Attributes:`.
  - A test's docstring states the behaviour it protects, in plain words: "A disabled CDN never
    receives a viewer", not "test disabled".
- **Comments explain why, not what.** `# Newest first, so the first rows are the latest probes`
  helps. `# loop over rows` does not. Explain anything a newcomer would have to look up.
- **Docstrings stay true.** When you change what a function does, update its docstring in the
  same commit. A docstring that describes the old behaviour is worse than none.
- The linter enforces the docstring rules (`D` in `pyproject.toml`, Google convention), so
  `make lint` fails on a missing or malformed docstring.

Example:

```python
def provider_health(conn: sqlite3.Connection, region: str, window: int) -> dict[str, dict]:
    """Compute error rate and latency for each provider in a region.

    Args:
        conn: Open database connection.
        region: Region to report on, e.g. ``"eu-west"``.
        window: Number of recent probes per provider.

    Returns:
        A mapping of provider name to its statistics.
    """
```

FastAPI shows an endpoint's docstring as its description at `/docs`, so write endpoint docstrings
for the people who call the API too.

## Tests

Every change comes with tests, written to the same standard as the existing suite in `tests/`.

- **One behaviour per test**, named and described as that behaviour:
  `test_delete_twice_returns_404_the_second_time`.
- **Test the failure paths, not only the happy path.** For each endpoint or function: invalid
  input, missing input, the edges of every range (0, 100, 101), not found, duplicates, empty
  data, and what happens when a dependency fails.
- **Assert everything that matters.** Check the status code *and* the whole body
  (`assert response.json() == {...}`), not just that a body exists. After a write, check the
  stored state too (fetch it again), so the test proves the change was saved and not only
  echoed back. After a rejected request, check that nothing changed.
- **Expected errors are asserted explicitly** with `pytest.raises(...)`. Any other exception
  fails the test on its own, so "returns None for garbage" also proves nothing was raised.
- **Use `pytest.mark.parametrize`** to run one test over many inputs, rather than copying it or
  looping inside it. Each case then passes or fails on its own, with a readable ID.
- **Deterministic, always.** No test may depend on luck, timing or the order tests run in. Set up
  a case with only one right answer, or replace the source of randomness with `monkeypatch`.
  A test that "sometimes fails" is a bug in the test or the code. Find out which: never skip it.
- **Unit tests** call one module's functions directly (`test_ingest.py`). **API tests** send
  HTTP requests through `TestClient` (`test_cdns.py`). Write both: unit tests pin down the
  logic, API tests prove the pieces are wired together.
- **A test must be able to fail.** Before trusting a new test, break the code it covers (flip a
  condition, delete a line) and watch the test go red. If it stays green, it isn't testing
  anything.

## Before you push

```bash
make lint
make test
```

## Pre-commit hooks

We use [pre-commit](https://pre-commit.com) to run the linter, the formatter and the
commit-message check on your machine before code reaches CI.

```bash
uv tool install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files
```

## Pull requests

- One ticket per PR. Put the ticket number in the title: `NWM-102: Probe ingestion`.
- Fill in the PR template: what changed, why, how you tested it, risks and rollback.
- Keep PRs small enough to review in 20 minutes. Split larger work.
- CI must be green before merging. Prefer "Squash and merge" or "Rebase and merge" so `main`
  stays linear.

## Configuration and secrets

- All configuration comes from environment variables prefixed `EDGEROUTE_`, documented in the
  README.
- Never commit secrets, tokens, local databases or generated files.

## Decisions

Significant design decisions are recorded as Architecture Decision Records in `docs/adr/`, using
[the template](adr/0000-template.md). Number them in order.

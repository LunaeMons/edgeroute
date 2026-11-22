"""Tests for the seed script (``scripts/seed.py``)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import seed


def _expected() -> list[dict]:
    """Return the providers listed in ``data/cdns.json``, sorted by name like the API.

    Returns:
        The provider definitions from the data file.
    """
    return sorted(json.loads(seed.DATA.read_text()), key=lambda cdn: cdn["name"])


def test_seed_loads_every_provider_in_the_data_file(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Seeding an empty database registers every provider with its configured values.

    Args:
        client: Test client with a fresh database (the seed writes to the same file).
        capsys: Captures what the script prints (built-in fixture).
    """
    seed.main()

    stored = client.get("/api/v1/cdns").json()
    fields = ("name", "weight", "enabled", "cost_per_gb_cents")
    assert [{f: cdn[f] for f in fields} for cdn in stored] == [
        {f: cdn[f] for f in fields} for cdn in _expected()
    ]
    assert capsys.readouterr().out.count("added") == len(_expected())


def test_seed_twice_does_not_duplicate_providers(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Running the seed again skips the providers that exist and adds nothing.

    Args:
        client: Test client with a fresh database.
        capsys: Captures what the script prints (built-in fixture).
    """
    seed.main()
    capsys.readouterr()  # Discard the output of the first run.

    seed.main()

    assert len(client.get("/api/v1/cdns").json()) == len(_expected())
    output = capsys.readouterr().out
    assert output.count("skip") == len(_expected())
    assert "added" not in output


def test_seed_runs_as_a_command(db_path: Path) -> None:
    """``python -m scripts.seed``, the command behind ``make seed``, succeeds from a shell.

    The script runs in a separate process, as a developer would run it, with the test
    database passed through the environment.

    Args:
        db_path: Path of a fresh database file.
    """
    result = subprocess.run(  # noqa: S603 - fixed arguments, no shell, no user input
        [sys.executable, "-m", "scripts.seed"],
        capture_output=True,
        text=True,
        env=os.environ | {"EDGEROUTE_DB_PATH": str(db_path)},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("added") == len(_expected())

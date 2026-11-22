"""Tests for reading settings from the environment (``app.config``)."""

import dataclasses

import pytest

from app.config import get_settings


def test_defaults_apply_when_the_environment_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without environment variables, the local-development defaults are used.

    Args:
        monkeypatch: Removes the variables for this test only.
    """
    monkeypatch.delenv("EDGEROUTE_DB_PATH", raising=False)
    monkeypatch.delenv("EDGEROUTE_PROBE_WINDOW", raising=False)

    settings = get_settings()

    assert settings.db_path == "edgeroute.db"
    assert settings.probe_window == 50


def test_environment_variables_override_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Values in the environment win over the defaults, and the window becomes an int.

    Args:
        monkeypatch: Sets the variables for this test only.
    """
    monkeypatch.setenv("EDGEROUTE_DB_PATH", "/data/edgeroute.db")
    monkeypatch.setenv("EDGEROUTE_PROBE_WINDOW", "20")

    settings = get_settings()

    assert settings.db_path == "/data/edgeroute.db"
    assert settings.probe_window == 20


def test_settings_are_read_on_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """A change to the environment is visible to the next call, without a restart.

    Args:
        monkeypatch: Sets the variable for this test only.
    """
    monkeypatch.setenv("EDGEROUTE_PROBE_WINDOW", "10")
    first = get_settings()
    monkeypatch.setenv("EDGEROUTE_PROBE_WINDOW", "30")

    second = get_settings()

    assert (first.probe_window, second.probe_window) == (10, 30)


def test_a_non_numeric_probe_window_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A probe window that is not a whole number fails loudly instead of being guessed.

    Args:
        monkeypatch: Sets the variable for this test only.
    """
    monkeypatch.setenv("EDGEROUTE_PROBE_WINDOW", "fifty")

    with pytest.raises(ValueError, match="fifty"):
        get_settings()


def test_settings_cannot_be_changed_at_runtime() -> None:
    """Settings are read-only: assigning to a field raises an error."""
    settings = get_settings()

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.probe_window = 1  # type: ignore[misc]

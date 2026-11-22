"""Application settings, read from environment variables.

Keeping configuration in the environment, rather than in the code, lets the same code
(and the same container image) run on a laptop, in CI and in production with different
values. See "The Twelve-Factor App", factor III: https://12factor.net/config

Example:
    Read the settings anywhere in the application::

        from app.config import get_settings

        window = get_settings().probe_window
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the service.

    ``frozen=True`` makes instances read-only, so no part of the code can change a
    setting by accident while the application is running.

    Attributes:
        db_path: Path to the SQLite database file.
        admin_token: Shared secret that admin endpoints expect in the ``X-Admin-Token``
            header.
        probe_window: How many recent probes per CDN and region feed the health
            calculation.
    """

    db_path: str
    admin_token: str
    probe_window: int


def get_settings() -> Settings:
    """Build the settings from the current environment.

    The environment is read on every call rather than once at import time, so tests can
    change a variable (for example with pytest's ``monkeypatch``) and see the effect
    straight away.

    Returns:
        The resolved settings.

    Raises:
        ValueError: If ``EDGEROUTE_PROBE_WINDOW`` is not a whole number.
    """
    # Each setting falls back to a default that is convenient for local development.
    return Settings(
        db_path=os.environ.get("EDGEROUTE_DB_PATH", "edgeroute.db"),
        admin_token=os.environ.get("ADMIN_TOKEN", "changeme"),
        probe_window=int(os.environ.get("EDGEROUTE_PROBE_WINDOW", "50")),
    )

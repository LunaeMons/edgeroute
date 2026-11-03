"""Application settings, read from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the service.

    Attributes:
        db_path: Path to the SQLite database file.
        admin_token: Shared secret required by admin endpoints (X-Admin-Token header).
        probe_window: How many recent probes per CDN and region feed the health calculation.
    """

    db_path: str
    admin_token: str
    probe_window: int


def get_settings() -> Settings:
    """Build the settings from the current environment.

    Returns:
        The resolved settings.
    """
    return Settings(
        db_path=os.environ.get("EDGEROUTE_DB_PATH", "edgeroute.db"),
        admin_token=os.environ.get("ADMIN_TOKEN", "changeme"),
        probe_window=int(os.environ.get("EDGEROUTE_PROBE_WINDOW", "50")),
    )

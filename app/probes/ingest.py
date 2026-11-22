"""Ingestion of CDN probe exports (partial implementation, see NWM-102).

Probe agents in each region regularly request a test object from every CDN and record
what happened: the HTTP status and the time to first byte (TTFB). The operations team
uploads their exports here. The formats are described in ``docs/vendor-feeds.md``.

The import runs in three steps:

1. Parse the file into rows (:func:`parse_csv` or :func:`parse_jsonl`).
2. Validate each row and map it to the ``Probe`` model (:func:`validate_row`).
3. Store the valid rows and report the rejected ones (:func:`process_import`).
"""

import csv
import io
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.probes.models import Probe

# Fields of the ``Probe`` model that every stored probe must have a value for.
REQUIRED_FIELDS = ("observed_at", "provider", "region", "status_code", "ttfb_ms")


def parse_csv(content: str) -> list[dict[str, Any]]:
    """Parse a CSV export into row dictionaries.

    Args:
        content: Raw CSV text, header row first.

    Returns:
        One dictionary per data row, keyed by the header names. Every value is a
        string, because CSV has no types.
    """
    # ``DictReader`` expects a file; ``StringIO`` wraps the text so it behaves like one.
    return list(csv.DictReader(io.StringIO(content)))


def parse_jsonl(content: str) -> list[dict[str, Any]]:
    """Parse a JSON Lines export into row dictionaries.

    JSON Lines is one complete JSON object per line, which lets an agent append to a
    file without rewriting it.

    Args:
        content: Raw JSONL text, one JSON object per line.

    Returns:
        One dictionary per non-empty line, with JSON types preserved (numbers stay
        numbers).
    """
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def normalise_ttfb(raw: Any) -> float | None:
    """Convert a time-to-first-byte value to milliseconds.

    Accepts ``"143ms"``, ``"143"``, ``143`` or ``143.0``.

    Args:
        raw: The raw value from the export.

    Returns:
        The TTFB in milliseconds, or None if it cannot be parsed.

    Examples:
        >>> normalise_ttfb("143ms")
        143.0
        >>> normalise_ttfb("n/a") is None
        True
    """
    if raw is None or raw == "":
        return None
    # Numbers (from JSON) need no parsing.
    if isinstance(raw, int | float):
        return float(raw)
    # Text (from CSV): drop an optional "ms" suffix, then parse what is left.
    text = str(raw).strip().lower()
    if text.endswith("ms"):
        text = text[:-2]
    try:
        return float(text)
    except ValueError:
        return None


def parse_timestamp(raw: Any) -> str | None:
    """Parse an ISO 8601 timestamp.

    Args:
        raw: The raw timestamp text, e.g. ``"2026-11-17T08:00:11"``.

    Returns:
        The timestamp in ISO format, or None if it is empty or cannot be parsed.
    """
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).strip()).isoformat()
    except ValueError:
        return None


def _to_int(raw: Any) -> int | None:
    """Convert a value to an integer, without raising.

    Args:
        raw: The raw value, e.g. ``"200"`` or ``200``.

    Returns:
        The integer, or None if the value is missing or not a whole number.
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def validate_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Validate one export row and map it to the probe table.

    Args:
        row: A parsed row from a CSV or JSONL export.

    Returns:
        The row ready for insertion, keyed by the ``Probe`` model's field names, or
        None if a required field is missing or invalid.
    """
    # Map the export's field names to the Probe model's fields, cleaning each value.
    # Names are trimmed and lowercased so " Aurora " and "aurora" are the same CDN.
    transformed = {
        "observed_at": parse_timestamp(row.get("timestamp")),
        "provider": (row.get("cdn_name") or "").strip().lower() or None,
        "region": (row.get("region") or "").strip().lower() or None,
        "status_code": _to_int(row.get("status")),
        "ttfb_ms": normalise_ttfb(row.get("ttfb")),
    }
    # Reject the row if any required value is missing.
    if not all(transformed[field] for field in REQUIRED_FIELDS):
        return None
    return transformed


def process_import(session: Session, content: str, file_format: str) -> dict[str, Any]:
    """Run the import for one uploaded file.

    The probes are added to the session; they are saved when the caller commits.

    Args:
        session: Open database session.
        content: The file's text.
        file_format: ``"csv"`` or ``"jsonl"``.

    Returns:
        A summary with ``total``, ``imported`` and ``rejected`` counts, and ``errors``:
        one entry per rejected row with its line number and the reason.
    """
    rows = parse_jsonl(content) if file_format == "jsonl" else parse_csv(content)
    imported = 0
    errors: list[dict[str, Any]] = []
    # ``enumerate(..., start=1)`` numbers the rows from 1, as a person would count them.
    for line, row in enumerate(rows, start=1):
        probe = validate_row(row)
        if probe is None:
            errors.append({"line": line, "reason": "Missing required fields."})
            continue
        # ``**probe`` passes the dictionary's keys as keyword arguments:
        # Probe(observed_at=..., provider=..., ...).
        session.add(Probe(**probe))
        imported += 1
    return {"total": len(rows), "imported": imported, "rejected": len(errors), "errors": errors}

"""Ingestion of CDN probe exports (partial implementation, see NWM-102)."""
import csv
import io
import json
import sqlite3
from datetime import datetime
from typing import Any

REQUIRED_FIELDS = ("observed_at", "provider", "region", "status_code", "ttfb_ms")


def parse_csv(content: str) -> list[dict[str, Any]]:
    """Parse a CSV export into row dictionaries.

    Args:
        content: Raw CSV text, header row first.

    Returns:
        One dictionary per data row.
    """
    return list(csv.DictReader(io.StringIO(content)))


def parse_jsonl(content: str) -> list[dict[str, Any]]:
    """Parse a JSON Lines export into row dictionaries.

    Args:
        content: Raw JSONL text, one JSON object per line.

    Returns:
        One dictionary per non-empty line.
    """
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def normalise_ttfb(raw: Any) -> float | None:
    """Convert a time-to-first-byte value to milliseconds.

    Accepts "143ms", "143", 143 or 143.0.

    Args:
        raw: The raw value from the export.

    Returns:
        The TTFB in milliseconds, or None if it cannot be parsed.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, int | float):
        return float(raw)
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
        raw: The raw timestamp text.

    Returns:
        The timestamp in ISO format, or None if it cannot be parsed.
    """
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).strip()).isoformat()
    except ValueError:
        return None


def _to_int(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def validate_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Validate one export row and map it to the probe table.

    Args:
        row: A parsed row from a CSV or JSONL export.

    Returns:
        The row ready for insertion, or None if a required field is missing.
    """
    transformed = {
        "observed_at": parse_timestamp(row.get("timestamp")),
        "provider": (row.get("cdn_name") or "").strip().lower() or None,
        "region": (row.get("region") or "").strip().lower() or None,
        "status_code": _to_int(row.get("status")),
        "ttfb_ms": normalise_ttfb(row.get("ttfb")),
    }
    if not all(transformed[field] for field in REQUIRED_FIELDS):
        return None
    return transformed


def process_import(conn: sqlite3.Connection, content: str, file_format: str) -> dict[str, Any]:
    """Run the import for one uploaded file.

    Args:
        conn: Open database connection.
        content: The file's text.
        file_format: "csv" or "jsonl".

    Returns:
        A summary with counts and the rows that were rejected.
    """
    rows = parse_jsonl(content) if file_format == "jsonl" else parse_csv(content)
    imported = 0
    errors: list[dict[str, Any]] = []
    for line, row in enumerate(rows, start=1):
        probe = validate_row(row)
        if probe is None:
            errors.append({"line": line, "reason": "Missing required fields."})
            continue
        conn.execute(
            "INSERT INTO probe (observed_at, provider, region, status_code, ttfb_ms) "
            "VALUES (:observed_at, :provider, :region, :status_code, :ttfb_ms)",
            probe,
        )
        imported += 1
    return {"total": len(rows), "imported": imported, "rejected": len(errors), "errors": errors}

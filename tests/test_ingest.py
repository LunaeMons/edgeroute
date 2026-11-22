"""Unit tests for parsing and validating probe exports (``app.probes.ingest``).

These call the functions directly, without HTTP. A note on errors: if a function under
test raises an exception that the test did not expect, pytest reports the test as
failed. So a test like "garbage becomes None" also proves that no exception escapes.
Where raising IS the expected behaviour, the test says so with ``pytest.raises``.
"""

import json
import sqlite3
from typing import Any

import pytest

from app.probes import ingest

# A valid row as the probe export provides it, before validation.
VALID_ROW = {
    "timestamp": "2026-11-17 08:00:00",
    "cdn_name": " Aurora ",
    "region": "eu-west",
    "status": "200",
    "ttfb": "120ms",
}

# The same row after validation, keyed by the probe table's columns.
VALID_PROBE = {
    "observed_at": "2026-11-17T08:00:00",
    "provider": "aurora",
    "region": "eu-west",
    "status_code": 200,
    "ttfb_ms": 120.0,
}


# --- Parsing ------------------------------------------------------------------------


def test_parse_csv_returns_one_dict_per_row_keyed_by_header() -> None:
    """Each data row becomes a dictionary keyed by the header names, values as text."""
    content = (
        "timestamp,region,status\n"
        "2026-11-17 08:00:00,eu-west,200\n"
        "2026-11-17 08:01:00,eu-south,503\n"
    )

    rows = ingest.parse_csv(content)

    assert rows == [
        {"timestamp": "2026-11-17 08:00:00", "region": "eu-west", "status": "200"},
        {"timestamp": "2026-11-17 08:01:00", "region": "eu-south", "status": "503"},
    ]


@pytest.mark.parametrize("content", ["", "timestamp,region,status\n"], ids=["empty", "header-only"])
def test_parse_csv_without_data_rows_returns_an_empty_list(content: str) -> None:
    """An empty file, or a file with only a header, has no rows.

    Args:
        content: CSV text without data rows.
    """
    assert ingest.parse_csv(content) == []


def test_parse_jsonl_preserves_types_and_skips_blank_lines() -> None:
    """Each non-blank line becomes a dictionary; numbers stay numbers, blank lines are ignored."""
    content = '{"region": "eu-west", "status": 200}\n\n   \n{"region": "eu-south", "status": 0}\n'

    rows = ingest.parse_jsonl(content)

    assert rows == [{"region": "eu-west", "status": 200}, {"region": "eu-south", "status": 0}]


def test_parse_jsonl_raises_on_a_line_that_is_not_json() -> None:
    """A line that is not valid JSON raises ``JSONDecodeError`` rather than being skipped."""
    with pytest.raises(json.JSONDecodeError):
        ingest.parse_jsonl('{"region": "eu-west"}\nnot json\n')


# --- Field normalisation ------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("143ms", 143.0),
        ("143", 143.0),
        ("12.5ms", 12.5),
        (" 143MS ", 143.0),
        (" 143 ms", 143.0),
        (143, 143.0),
        (143.5, 143.5),
    ],
)
def test_normalise_ttfb_accepts_milliseconds(raw: Any, expected: float) -> None:
    """TTFB written as text (with or without "ms", any case or spacing) or a number becomes a float.

    Args:
        raw: The value as it appears in an export.
        expected: The TTFB in milliseconds.
    """
    result = ingest.normalise_ttfb(raw)

    assert result == expected
    assert isinstance(result, float)


@pytest.mark.parametrize("raw", [None, "", "   ", "n/a", "ms", "fast", "1,5ms", "12 3"])
def test_normalise_ttfb_returns_none_for_values_it_cannot_parse(raw: Any) -> None:
    """Missing or non-numeric values become None, and no exception escapes.

    Args:
        raw: A value that is not a time.
    """
    assert ingest.normalise_ttfb(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-11-17 08:00:11", "2026-11-17T08:00:11"),
        ("2026-11-17T08:00:11", "2026-11-17T08:00:11"),
        (" 2026-11-17 08:00:11 ", "2026-11-17T08:00:11"),
        ("2026-11-17T08:00:11+00:00", "2026-11-17T08:00:11+00:00"),
    ],
)
def test_parse_timestamp_returns_iso_8601(raw: str, expected: str) -> None:
    """Valid timestamps come back in ISO 8601 form, with a "T" between date and time.

    Args:
        raw: A timestamp as it appears in an export.
        expected: The normalised timestamp.
    """
    assert ingest.parse_timestamp(raw) == expected


@pytest.mark.parametrize(
    "raw", [None, "", "yesterday", "17/11/2026 08:00", "2026-13-01 00:00:00", "2026-11-31 00:00"]
)
def test_parse_timestamp_returns_none_for_invalid_values(raw: Any) -> None:
    """Missing, malformed or impossible dates (month 13, 31 November) become None.

    Args:
        raw: A value that is not a valid timestamp.
    """
    assert ingest.parse_timestamp(raw) is None


# --- Row validation -----------------------------------------------------------------


def test_validate_row_maps_fields() -> None:
    """A valid row is mapped to the probe table's columns and its values are cleaned.

    The provider name is trimmed and lowercased, the status becomes an integer, the
    TTFB becomes milliseconds and the timestamp becomes ISO 8601.
    """
    assert ingest.validate_row(VALID_ROW) == VALID_PROBE


def test_validate_row_lowercases_and_trims_the_region() -> None:
    """Regions are compared in lowercase without spaces, like provider names."""
    probe = ingest.validate_row(VALID_ROW | {"region": " EU-West "})

    assert probe is not None
    assert probe["region"] == "eu-west"


def test_validate_row_ignores_extra_fields() -> None:
    """Fields the probe table does not use are dropped, not rejected."""
    assert ingest.validate_row(VALID_ROW | {"agent_version": "1.4.2"}) == VALID_PROBE


def test_validate_row_does_not_modify_its_input() -> None:
    """Validation builds a new dictionary and leaves the parsed row untouched."""
    row = dict(VALID_ROW)

    ingest.validate_row(row)

    assert row == VALID_ROW


@pytest.mark.parametrize("missing", ["timestamp", "cdn_name", "region", "status", "ttfb"])
def test_validate_row_rejects_a_missing_field(missing: str) -> None:
    """A row without any one of the required fields is rejected: None is returned.

    Args:
        missing: The field removed from an otherwise valid row.
    """
    row = {key: value for key, value in VALID_ROW.items() if key != missing}

    assert ingest.validate_row(row) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("timestamp", "yesterday"),
        ("cdn_name", "   "),
        ("region", ""),
        ("status", "OK"),
        ("status", "2.5"),
        ("ttfb", "fast"),
    ],
)
def test_validate_row_rejects_an_invalid_value(field: str, value: str) -> None:
    """A row with a blank or unparseable required value is rejected: None is returned.

    Args:
        field: The field given an invalid value.
        value: The invalid value.
    """
    assert ingest.validate_row(VALID_ROW | {field: value}) is None


# --- Whole import -------------------------------------------------------------------


def _stored_probes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every stored probe, in insertion order, without the generated ID.

    Args:
        conn: Open database connection.

    Returns:
        The probe rows as dictionaries.
    """
    rows = conn.execute(
        "SELECT observed_at, provider, region, status_code, ttfb_ms FROM probe ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]


def test_process_import_stores_valid_rows_and_reports_rejected_ones(
    conn: sqlite3.Connection,
) -> None:
    """Valid rows are stored; each invalid row is reported with its line number and reason.

    Line numbers count data rows from 1, so the header is not line 1.

    Args:
        conn: Connection to a fresh database.
    """
    content = (
        "timestamp,cdn_name,region,status,ttfb\n"
        "2026-11-17 08:00:00,aurora,eu-west,200,120ms\n"
        "2026-11-17 08:01:00,aurora,,200,130ms\n"
        "2026-11-17 08:02:00,meridian,eu-west,500,90ms\n"
        "not-a-date,meridian,eu-west,200,90ms\n"
    )

    summary = ingest.process_import(conn, content, "csv")

    assert summary == {
        "total": 4,
        "imported": 2,
        "rejected": 2,
        "errors": [
            {"line": 2, "reason": "Missing required fields."},
            {"line": 4, "reason": "Missing required fields."},
        ],
    }
    assert _stored_probes(conn) == [
        {
            "observed_at": "2026-11-17T08:00:00",
            "provider": "aurora",
            "region": "eu-west",
            "status_code": 200,
            "ttfb_ms": 120.0,
        },
        {
            "observed_at": "2026-11-17T08:02:00",
            "provider": "meridian",
            "region": "eu-west",
            "status_code": 500,
            "ttfb_ms": 90.0,
        },
    ]


def test_process_import_uses_the_jsonl_parser_for_jsonl(conn: sqlite3.Connection) -> None:
    """With ``file_format="jsonl"`` the content is read as JSON Lines.

    Args:
        conn: Connection to a fresh database.
    """
    content = json.dumps(VALID_ROW) + "\n"

    summary = ingest.process_import(conn, content, "jsonl")

    assert summary == {"total": 1, "imported": 1, "rejected": 0, "errors": []}
    assert _stored_probes(conn) == [VALID_PROBE]


def test_process_import_of_an_empty_file_stores_nothing(conn: sqlite3.Connection) -> None:
    """An empty export is a valid, empty import: all counts are zero.

    Args:
        conn: Connection to a fresh database.
    """
    summary = ingest.process_import(conn, "", "csv")

    assert summary == {"total": 0, "imported": 0, "rejected": 0, "errors": []}
    assert _stored_probes(conn) == []


def test_process_import_with_only_invalid_rows_stores_nothing(conn: sqlite3.Connection) -> None:
    """When every row is invalid, every row is reported and nothing is stored.

    Args:
        conn: Connection to a fresh database.
    """
    # Both rows lack a timestamp.
    content = (
        "timestamp,cdn_name,region,status,ttfb\n,aurora,eu-west,200,1ms\n,aurora,eu-west,200,1ms\n"
    )

    summary = ingest.process_import(conn, content, "csv")

    assert (summary["total"], summary["imported"], summary["rejected"]) == (2, 0, 2)
    assert [error["line"] for error in summary["errors"]] == [1, 2]
    assert _stored_probes(conn) == []

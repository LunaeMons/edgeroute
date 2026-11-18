"""HTTP endpoints for probe data."""
import sqlite3

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth import require_admin
from app.config import get_settings
from app.db import get_conn
from app.probes import health, ingest

router = APIRouter(prefix="/api/v1/probes", tags=["probes"])


@router.post("/import", dependencies=[Depends(require_admin)])
async def import_probes(
    file: UploadFile = File(...), conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    """Import a probe export (CSV or JSONL) from the probe agents (admin only)."""
    filename = file.filename or ""
    file_format = "jsonl" if filename.endswith(".json") else "csv"
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be UTF-8 text."
        ) from exc
    return ingest.process_import(conn, content, file_format)


@router.get("/health/{region}")
def region_health(region: str, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Show error rate and latency per CDN for a region."""
    return {
        "region": region,
        "window": get_settings().probe_window,
        "providers": health.provider_health(conn, region, get_settings().probe_window),
    }

"""HTTP endpoints for probe data, under ``/api/v1/probes``.

* ``POST /import`` uploads a probe export (admin only).
* ``GET /health/{region}`` reports the health of every CDN in a region (public).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.config import get_settings
from app.db import get_session
from app.probes import health, ingest

router = APIRouter(prefix="/api/v1/probes", tags=["probes"])


@router.post("/import", dependencies=[Depends(require_admin)])
async def import_probes(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> dict:
    """Import a probe export (CSV or JSONL) from the probe agents (admin only).

    The file is sent as a multipart form upload, the way a browser's file picker sends
    it. With curl: ``curl -F file=@probes.csv -H "X-Admin-Token: ..." <url>``.

    Args:
        file: The uploaded export, from the ``file`` form field.
        session: Database session, provided by FastAPI.

    Returns:
        The import summary: counts of total, imported and rejected rows, and the
        reason for each rejection.

    Raises:
        HTTPException: 400 Bad Request if the file is not UTF-8 text.
    """
    # Pick the parser from the file extension.
    filename = file.filename or ""
    file_format = "jsonl" if filename.endswith(".json") else "csv"
    try:
        # Uploads arrive as bytes; decode them to text before parsing.
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be UTF-8 text."
        ) from exc
    return ingest.process_import(session, content, file_format)


@router.get("/health/{region}")
def region_health(region: str, session: Session = Depends(get_session)) -> dict:
    """Show error rate and latency per CDN for a region.

    Args:
        region: The region to report on, from the URL path, e.g. ``eu-west``.
        session: Database session, provided by FastAPI.

    Returns:
        The region, the probe window used, and the statistics for each provider.
    """
    return {
        "region": region,
        "window": get_settings().probe_window,
        "providers": health.provider_health(session, region, get_settings().probe_window),
    }

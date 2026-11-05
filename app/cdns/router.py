"""HTTP endpoints for CDN providers."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin
from app.cdns import repository
from app.cdns.schemas import Cdn, CdnCreate, CdnUpdate
from app.db import get_conn

router = APIRouter(prefix="/api/v1/cdns", tags=["cdns"])


@router.get("", response_model=list[Cdn])
def list_cdns(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    """List all CDN providers."""
    return repository.list_cdns(conn)


@router.get("/{cdn_id}", response_model=Cdn)
def get_cdn(cdn_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Fetch one CDN provider."""
    cdn = repository.get_cdn(conn, cdn_id)
    if cdn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CDN not found.")
    return cdn


@router.post(
    "",
    response_model=Cdn,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_cdn(payload: CdnCreate, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Register a CDN provider (admin only)."""
    try:
        return repository.create_cdn(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{cdn_id}", response_model=Cdn, dependencies=[Depends(require_admin)])
def update_cdn(
    cdn_id: int, payload: CdnUpdate, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    """Change a CDN provider (admin only)."""
    cdn = repository.update_cdn(conn, cdn_id, payload)
    if cdn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CDN not found.")
    return cdn


@router.delete(
    "/{cdn_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_cdn(cdn_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> None:
    """Remove a CDN provider (admin only)."""
    if not repository.delete_cdn(conn, cdn_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CDN not found.")

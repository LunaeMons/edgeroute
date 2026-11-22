"""HTTP endpoints for CDN providers, under ``/api/v1/cdns``.

Anyone can read the list of CDNs. Creating, changing and deleting one requires the
admin token (see :mod:`app.auth`).

The endpoints stay thin: they translate between HTTP and the repository, turning a
missing provider into a 404 and a duplicate name into a 409.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin
from app.cdns import repository
from app.cdns.schemas import Cdn, CdnCreate, CdnUpdate
from app.db import get_conn

router = APIRouter(prefix="/api/v1/cdns", tags=["cdns"])


@router.get("", response_model=list[Cdn])
def list_cdns(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    """List all CDN providers.

    Args:
        conn: Database connection, provided by FastAPI.

    Returns:
        Every registered provider, ordered by name.
    """
    return repository.list_cdns(conn)


@router.get("/{cdn_id}", response_model=Cdn)
def get_cdn(cdn_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Fetch one CDN provider.

    Args:
        cdn_id: The provider's ID, from the URL path.
        conn: Database connection, provided by FastAPI.

    Returns:
        The provider.

    Raises:
        HTTPException: 404 if no provider has that ID.
    """
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
    """Register a CDN provider (admin only).

    Args:
        payload: The new provider, from the JSON request body.
        conn: Database connection, provided by FastAPI.

    Returns:
        The stored provider.

    Raises:
        HTTPException: 409 Conflict if a provider with that name already exists.
    """
    try:
        return repository.create_cdn(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{cdn_id}", response_model=Cdn, dependencies=[Depends(require_admin)])
def update_cdn(
    cdn_id: int, payload: CdnUpdate, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    """Change some fields of a CDN provider (admin only).

    Args:
        cdn_id: The provider's ID, from the URL path.
        payload: The fields to change, from the JSON request body.
        conn: Database connection, provided by FastAPI.

    Returns:
        The provider after the change.

    Raises:
        HTTPException: 404 if no provider has that ID.
    """
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
    """Remove a CDN provider (admin only).

    Args:
        cdn_id: The provider's ID, from the URL path.
        conn: Database connection, provided by FastAPI.

    Raises:
        HTTPException: 404 if no provider has that ID.
    """
    if not repository.delete_cdn(conn, cdn_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CDN not found.")

"""HTTP endpoint that steers a viewer to a CDN.

This is the endpoint video players call before playback starts. It is public (no admin
token) and sits on the critical path of every playback start, so it must be fast and
reliable.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.db import get_conn
from app.steering import service

router = APIRouter(prefix="/api/v1", tags=["steering"])


class SteeringDecision(BaseModel):
    """Where the player should fetch the asset from.

    Attributes:
        cdn: Name of the chosen CDN provider.
        url: Full URL of the asset on that CDN.
        region: The viewer's region, echoed back from the request.
    """

    cdn: str
    url: str
    region: str


@router.get("/steer", response_model=SteeringDecision)
def steer(
    region: str = Query(..., examples=["eu-west"]),
    asset: str = Query(..., examples=["/live/nw1/master.m3u8"]),
    session_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> SteeringDecision:
    """Return the CDN URL a player should use for an asset.

    Args:
        region: The viewer's region, from the ``region`` query parameter.
        asset: Path of the asset to play, from the ``asset`` query parameter.
        session_id: The player session, from the optional ``session_id`` query
            parameter.
        conn: Database connection, provided by FastAPI.

    Returns:
        The chosen CDN and the full URL to fetch the asset from.

    Raises:
        HTTPException: 503 Service Unavailable if no CDN can take the viewer.
    """
    cdn = service.choose_cdn(conn, region=region, session_id=session_id)
    if cdn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No CDN available."
        )
    # Join the two parts with exactly one slash, whether or not the base URL ends with
    # one or the asset path starts with one.
    url = cdn["base_url"].rstrip("/") + "/" + asset.lstrip("/")
    return SteeringDecision(cdn=cdn["name"], url=url, region=region)

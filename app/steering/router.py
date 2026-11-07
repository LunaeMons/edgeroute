"""HTTP endpoint that steers a viewer to a CDN."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.db import get_conn
from app.steering import service

router = APIRouter(prefix="/api/v1", tags=["steering"])


class SteeringDecision(BaseModel):
    """Where the player should fetch the asset from."""

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
    """Return the CDN URL a player should use for an asset."""
    cdn = service.choose_cdn(conn, region=region, session_id=session_id)
    if cdn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No CDN available."
        )
    url = cdn["base_url"].rstrip("/") + "/" + asset.lstrip("/")
    return SteeringDecision(cdn=cdn["name"], url=url, region=region)

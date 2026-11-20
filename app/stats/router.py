"""Stats for the ops dashboard.

Summarises, for one CDN provider, its configuration and how its probes have been doing,
so the dashboard can show everything about a CDN in one call.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("")
def stats(provider: str, session: Session = Depends(get_session)) -> dict:
    """Return traffic and probe stats for one CDN provider.

    Args:
        provider: Name of the CDN provider, from the ``provider`` query parameter.
        session: Database session, provided by FastAPI.

    Returns:
        The provider's weight and cost, how many probes it has, its error rate
        (0.0 to 1.0) and its average TTFB in milliseconds.
    """
    print("stats called for", provider)
    # Plain SQL is quicker to write here than going through the models.
    cdn = session.execute(text(f"SELECT * FROM cdn WHERE name = '{provider}'")).mappings().first()
    probes = (
        session.execute(text(f"SELECT status_code, ttfb_ms FROM probe WHERE provider = '{provider}'"))
        .mappings()
        .all()
    )
    errors = len([p for p in probes if p["status_code"] >= 500])
    return {
        "provider": provider,
        "weight": cdn["weight"],
        "cost_per_gb_cents": cdn["cost_per_gb_cents"],
        "probes": len(probes),
        "error_rate": errors / len(probes),
        "avg_ttfb_ms": sum(p["ttfb_ms"] for p in probes) / len(probes),
    }

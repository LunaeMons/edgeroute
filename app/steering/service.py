"""Steering logic: decide which CDN serves a viewer.

Steering is the core of EdgeRoute. Before playback starts, the video player asks which
CDN to fetch the stream from, and this module answers. Today it splits traffic across
the eligible CDNs in proportion to their weights.
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cdns.models import Cdn


def eligible_cdns(session: Session) -> list[Cdn]:
    """Return the CDN providers that may receive traffic.

    Args:
        session: Open database session.

    Returns:
        Enabled providers with a positive weight.
    """
    cdns = session.scalars(select(Cdn).order_by(Cdn.id))
    # Keep the providers that are switched on and have a share of the traffic.
    return [cdn for cdn in cdns if cdn.enabled and cdn.weight > 0]


def choose_cdn(session: Session, region: str, session_id: str | None = None) -> Cdn | None:
    """Pick a CDN for a viewer using the configured weights.

    Args:
        session: Open database session.
        region: The viewer's region, e.g. ``"eu-west"``.
        session_id: The player session, if known.

    Returns:
        The chosen provider, or None if no provider is eligible.
    """
    candidates = eligible_cdns(session)
    if not candidates:
        return None
    weights = [cdn.weight for cdn in candidates]
    # ``random.choices`` picks one candidate, each with a probability proportional to
    # its weight: with weights 50, 30 and 20, the first is picked about half the time.
    # The linter flags ``random`` as unsuitable for security (S311); this is load
    # balancing, not security, so the warning is silenced.
    return random.choices(candidates, weights=weights, k=1)[0]  # noqa: S311

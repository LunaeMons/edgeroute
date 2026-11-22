"""Database access for CDN providers.

The repository is the only module that reads and writes the ``cdn`` table. Endpoints
call these functions instead of querying the database themselves, which keeps database
code in one place and the endpoints short.

The functions work with a SQLAlchemy session and do not commit: the caller decides when
the unit of work is complete (for an HTTP request, :func:`app.db.get_session` commits
when the endpoint succeeds).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cdns.models import Cdn
from app.cdns.schemas import CdnCreate, CdnUpdate


def _stored_enabled(enabled: bool) -> str:
    """Convert the API's boolean to the value stored in the ``enabled`` column.

    Args:
        enabled: Whether the CDN may receive traffic.

    Returns:
        ``"true"`` or ``"false"``.
    """
    return "true" if enabled else "false"


def list_cdns(session: Session) -> list[Cdn]:
    """Return every CDN provider, ordered by name.

    Args:
        session: Open database session.

    Returns:
        The providers.
    """
    # ``select(Cdn)`` builds the query; ``scalars()`` returns Cdn objects rather than rows.
    return list(session.scalars(select(Cdn).order_by(Cdn.name)))


def get_cdn(session: Session, cdn_id: int) -> Cdn | None:
    """Return one CDN provider.

    Args:
        session: Open database session.
        cdn_id: The provider's ID.

    Returns:
        The provider, or None if it does not exist.
    """
    # ``session.get`` looks a row up by its primary key.
    return session.get(Cdn, cdn_id)


def create_cdn(session: Session, payload: CdnCreate) -> Cdn:
    """Insert a CDN provider.

    Args:
        session: Open database session.
        payload: Validated provider data.

    Returns:
        The stored provider, including its new ID and creation time.

    Raises:
        ValueError: If a provider with the same name already exists.
    """
    cdn = Cdn(
        name=payload.name,
        base_url=str(payload.base_url),
        weight=payload.weight,
        enabled=_stored_enabled(payload.enabled),
        cost_per_gb_cents=payload.cost_per_gb_cents,
    )
    session.add(cdn)
    try:
        # ``flush`` sends the INSERT now (still inside the transaction), so a duplicate
        # name fails here, where we can handle it, rather than later at commit.
        session.flush()
    except IntegrityError as exc:
        # The UNIQUE constraint on ``name`` rejected the insert. Undo it and raise a
        # plain ValueError, so callers don't need to know about database exceptions.
        session.rollback()
        raise ValueError(f"CDN '{payload.name}' already exists.") from exc
    # Load the values the database filled in (``created_at``).
    session.refresh(cdn)
    return cdn


def update_cdn(session: Session, cdn_id: int, payload: CdnUpdate) -> Cdn | None:
    """Apply a partial update to a CDN provider.

    Args:
        session: Open database session.
        cdn_id: The provider's ID.
        payload: Fields to change. Fields absent from the request are left alone.

    Returns:
        The updated provider, or None if it does not exist.
    """
    cdn = session.get(Cdn, cdn_id)
    if cdn is None:
        return None
    # ``exclude_unset=True`` keeps only the fields the client actually sent.
    changes = payload.model_dump(exclude_unset=True)
    # Convert values to the form they are stored in.
    if "enabled" in changes:
        changes["enabled"] = _stored_enabled(changes["enabled"])
    if "base_url" in changes:
        changes["base_url"] = str(changes["base_url"])
    # Setting an attribute marks the object as changed; the session writes it on flush.
    for field, value in changes.items():
        setattr(cdn, field, value)
    session.flush()
    return cdn


def delete_cdn(session: Session, cdn_id: int) -> bool:
    """Delete a CDN provider.

    Args:
        session: Open database session.
        cdn_id: The provider's ID.

    Returns:
        True if the provider was deleted, False if no provider had that ID.
    """
    cdn = session.get(Cdn, cdn_id)
    if cdn is None:
        return False
    session.delete(cdn)
    session.flush()
    return True

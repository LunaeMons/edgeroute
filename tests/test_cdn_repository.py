"""Unit tests for the CDN repository (``app.cdns.repository``), called without HTTP.

The API tests in ``test_cdns.py`` cover the endpoints. These cover repository behaviour
that a caller other than an HTTP request (a script, a future bulk import) relies on.
"""

import pytest
from sqlalchemy.orm import Session

from app.cdns import repository
from app.cdns.schemas import CdnCreate, CdnUpdate


def _payload(name: str) -> CdnCreate:
    """Build a valid CDN payload.

    Args:
        name: The CDN's name.

    Returns:
        A payload with that name and default values.
    """
    return CdnCreate(name=name, base_url="https://cdn.example")


def test_create_returns_the_stored_cdn_with_generated_fields(session: Session) -> None:
    """A created CDN has its ID and creation time filled in by the database.

    Args:
        session: Session on a fresh, migrated database.
    """
    cdn = repository.create_cdn(session, _payload("aurora"))

    assert cdn.id is not None
    assert cdn.created_at is not None
    assert (cdn.name, cdn.base_url, cdn.weight, cdn.enabled) == (
        "aurora",
        "https://cdn.example/",
        1,
        "true",
    )


def test_duplicate_raises_value_error_and_leaves_the_session_usable(session: Session) -> None:
    """After a duplicate name is rejected, the same session can still be used.

    Without the rollback in ``create_cdn``, SQLAlchemy refuses every further operation
    on a session whose flush failed, so a caller that handles the error and carries on
    (as the seed script could) would crash on its next query.

    Args:
        session: Session on a fresh, migrated database.
    """
    repository.create_cdn(session, _payload("aurora"))
    session.commit()

    with pytest.raises(ValueError, match="CDN 'aurora' already exists."):
        repository.create_cdn(session, _payload("aurora"))

    repository.create_cdn(session, _payload("kestrel"))
    assert [cdn.name for cdn in repository.list_cdns(session)] == ["aurora", "kestrel"]


def test_update_and_delete_return_nothing_for_an_unknown_id(session: Session) -> None:
    """Updating or deleting a CDN that does not exist reports it instead of raising.

    Args:
        session: Session on a fresh, migrated database.
    """
    assert repository.update_cdn(session, 999, CdnUpdate(weight=5)) is None
    assert repository.delete_cdn(session, 999) is False

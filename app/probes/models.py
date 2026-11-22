"""Database model for probe measurements: the ``probe`` table."""

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Probe(Base):
    """One measurement of one CDN, taken by a probe agent in one region.

    Attributes:
        id: Database identifier, assigned by the database.
        observed_at: When the probe ran, as ISO 8601 text.
        provider: Name of the CDN measured; matches ``Cdn.name``.
        region: Region the probe agent runs in, e.g. ``"eu-west"``.
        status_code: HTTP status the probe received.
        ttfb_ms: Time to first byte, in milliseconds.
    """

    __tablename__ = "probe"
    # The health report reads one region's probes, newest first. This index lets the
    # database find them without scanning the whole table.
    __table_args__ = (Index("ix_probe_region_observed_at", "region", "observed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    observed_at: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(32))
    status_code: Mapped[int]
    # Explicit column type, so the schema doesn't change with the SQLAlchemy version's
    # default mapping for ``float``.
    ttfb_ms: Mapped[float] = mapped_column(Float)

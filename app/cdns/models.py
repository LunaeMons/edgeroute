"""Database model for CDN providers: the ``cdn`` table.

A model is a Python class that describes a table. Each attribute annotated with
``Mapped[...]`` is a column; the type inside says what Python type the value has, and
``| None`` means the column may be empty (NULL).
"""

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Cdn(Base):
    """A CDN provider that EdgeRoute can steer viewers to.

    Attributes:
        id: Database identifier, assigned by the database.
        name: Unique short name, e.g. ``"aurora"``.
        base_url: Root URL that assets are served from.
        weight: Relative share of traffic, from 0 to 100.
        enabled: Whether the CDN may receive traffic: ``"true"`` or ``"false"``.
        cost_per_gb_cents: Price per gigabyte in cents, or None if unknown.
        created_at: When the provider was registered (UTC), set by the database.
    """

    __tablename__ = "cdn"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    base_url: Mapped[str] = mapped_column(String(2048))
    # ``default`` is used when Python creates a row; ``server_default`` is written into
    # the table definition, so rows inserted any other way get the same value.
    weight: Mapped[int] = mapped_column(default=1, server_default="1")
    enabled: Mapped[str] = mapped_column(String(5), default="true", server_default="true")
    cost_per_gb_cents: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

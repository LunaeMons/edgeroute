"""Request and response models for CDN providers.

These pydantic models are the API contract for ``/api/v1/cdns``. FastAPI uses them to
validate incoming JSON (an invalid body gets a 422 response with the reason), to shape
outgoing JSON, and to generate the OpenAPI document served at ``/docs``.
"""

from pydantic import BaseModel, Field, HttpUrl


class CdnCreate(BaseModel):
    """Payload to register a CDN provider.

    Attributes:
        name: Unique short name, lowercase letters, digits and hyphens only
            (e.g. ``"aurora"``).
        base_url: Root URL that assets are served from (e.g. ``"https://aurora.example"``).
        weight: Relative share of traffic, from 0 to 100. A CDN with weight 50 receives
            five times as many viewers as one with weight 10. Zero means no traffic.
        enabled: Whether the CDN may receive traffic at all.
        cost_per_gb_cents: Commercial price per gigabyte, in cents, if known.
    """

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    base_url: HttpUrl
    weight: int = Field(default=1, ge=0, le=100)
    enabled: bool = True
    cost_per_gb_cents: int | None = Field(default=None, ge=0)


class CdnUpdate(BaseModel):
    """Partial update for a CDN provider.

    Every field is optional: only the fields present in the request body are changed.
    The name cannot be changed.

    Attributes:
        base_url: New root URL.
        weight: New relative share of traffic, from 0 to 100.
        enabled: Switch the CDN on or off.
        cost_per_gb_cents: New price per gigabyte, in cents.
    """

    base_url: HttpUrl | None = None
    weight: int | None = Field(default=None, ge=0, le=100)
    enabled: bool | None = None
    cost_per_gb_cents: int | None = Field(default=None, ge=0)


class Cdn(BaseModel):
    """A CDN provider as stored and returned by the API.

    Attributes:
        id: Database identifier.
        name: Unique short name.
        base_url: Root URL that assets are served from.
        weight: Relative share of traffic, from 0 to 100.
        enabled: Whether the CDN may receive traffic.
        cost_per_gb_cents: Price per gigabyte in cents, or None if unknown.
        created_at: When the provider was registered (UTC, ``YYYY-MM-DD HH:MM:SS``).
    """

    id: int
    name: str
    base_url: str
    weight: int
    enabled: bool
    cost_per_gb_cents: int | None
    created_at: str

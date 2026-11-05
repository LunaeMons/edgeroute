"""Request and response models for CDN providers."""
from pydantic import BaseModel, Field, HttpUrl


class CdnCreate(BaseModel):
    """Payload to register a CDN provider."""

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    base_url: HttpUrl
    weight: int = Field(default=1, ge=0, le=100)
    enabled: bool = True
    cost_per_gb_cents: int | None = Field(default=None, ge=0)


class CdnUpdate(BaseModel):
    """Partial update for a CDN provider."""

    base_url: HttpUrl | None = None
    weight: int | None = Field(default=None, ge=0, le=100)
    enabled: bool | None = None
    cost_per_gb_cents: int | None = Field(default=None, ge=0)


class Cdn(BaseModel):
    """A CDN provider as stored."""

    id: int
    name: str
    base_url: str
    weight: int
    enabled: bool
    cost_per_gb_cents: int | None
    created_at: str

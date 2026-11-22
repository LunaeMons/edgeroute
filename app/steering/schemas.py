"""Response model for the steering endpoint: the contract video players rely on."""

from pydantic import BaseModel


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

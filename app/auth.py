"""Authentication for admin endpoints.

Endpoints that change data (registering CDNs, importing probes) are for the operations
team only. They require a shared secret in the ``X-Admin-Token`` HTTP header. Read-only
endpoints, such as steering, are public because video players call them.
"""

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_admin(x_admin_token: str = Header(...)) -> None:
    """Reject the request unless it carries the admin token (a FastAPI dependency).

    Attach it to an endpoint with ``dependencies=[Depends(require_admin)]``. FastAPI
    reads the ``X-Admin-Token`` header into ``x_admin_token``: it converts the
    parameter name from snake_case to the header name. ``Header(...)`` marks the header
    as required, so a request without it gets a 422 before this function runs.

    Args:
        x_admin_token: Value of the ``X-Admin-Token`` header.

    Raises:
        HTTPException: 401 Unauthorized when the token does not match the configured
            one.
    """
    if x_admin_token != get_settings().admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token.")

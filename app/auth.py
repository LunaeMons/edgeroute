"""Authentication for admin endpoints."""
from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_admin(x_admin_token: str = Header(...)) -> None:
    """Reject the request unless it carries the admin token.

    Args:
        x_admin_token: Value of the X-Admin-Token header.

    Raises:
        HTTPException: 401 when the token is wrong.
    """
    if x_admin_token != get_settings().admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token.")

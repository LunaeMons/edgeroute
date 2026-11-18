"""Application factory."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.cdns.router import router as cdn_router
from app.probes.router import router as probe_router
from app.steering.router import router as steering_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database before the app starts serving.

    Yields:
        Control back to FastAPI while the app runs.
    """
    db.init_db()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application.

    Returns:
        The configured application.
    """
    app = FastAPI(title="EdgeRoute", version="0.0.1", lifespan=lifespan)
    app.include_router(cdn_router)
    app.include_router(steering_router)
    app.include_router(probe_router)

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    return app


app = create_app()

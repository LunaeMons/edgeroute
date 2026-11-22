"""Application factory: builds the FastAPI app and wires the features together.

Run it locally with ``make run``. Uvicorn, the web server, imports the module-level
``app`` object defined at the bottom of this file. Once it is running, the interactive
API documentation is served at ``/docs``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.cdns.router import router as cdn_router
from app.probes.router import router as probe_router
from app.steering.router import router as steering_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database before the app starts serving requests.

    FastAPI runs the code before ``yield`` at start-up and the code after it at
    shutdown.

    Args:
        _: The application being started (unused).

    Yields:
        Control back to FastAPI while the app runs.
    """
    db.init_db()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory function, rather than a single global object, lets each test build a fresh
    app pointed at its own temporary database.

    Returns:
        The configured application, with every feature's endpoints registered.
    """
    app = FastAPI(title="EdgeRoute", version="0.0.1", lifespan=lifespan)

    # Each feature defines its endpoints on its own router; include them all here.
    app.include_router(cdn_router)
    app.include_router(steering_router)
    app.include_router(probe_router)

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        """Liveness probe: report that the process is up and answering HTTP.

        Returns:
            Always ``{"status": "ok"}``.
        """
        return {"status": "ok"}

    return app


app = create_app()

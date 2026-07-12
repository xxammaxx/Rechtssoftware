"""FastAPI application factory and lifecycle management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from private_legal_navigator.api.errors import CaseNotFoundError, case_not_found_handler
from private_legal_navigator.api.routes import router as case_router
from private_legal_navigator.config import Settings
from private_legal_navigator.infrastructure.sqlite_case_repository import (
    SqliteCaseRepository,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: ensure database directory and schema."""
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    repo: SqliteCaseRepository = app.state.repository
    repo.initialize_schema()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings. If None, defaults are loaded from
                  environment variables (PLN_DATA_DIR, PLN_HOST, PLN_PORT).

    Returns:
        A fully configured FastAPI application instance.
    """
    if settings is None:
        settings = Settings()

    # Ensure data directory exists and schema is initialized immediately
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    repository = SqliteCaseRepository(settings.database_path)
    repository.initialize_schema()

    app = FastAPI(
        title="PrivateLegalNavigator",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store settings and repository in app state for dependency injection
    app.state.settings = settings
    app.state.repository = repository

    # Register exception handlers
    app.add_exception_handler(CaseNotFoundError, case_not_found_handler)

    # Register routes
    app.include_router(case_router)

    # Health check
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

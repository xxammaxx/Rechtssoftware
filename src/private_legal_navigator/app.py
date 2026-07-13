"""FastAPI application factory and lifecycle management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from private_legal_navigator.api.document_routes import router as document_router
from private_legal_navigator.api.errors import (
    CaseNotFoundError,
    DocumentNotFoundError,
    case_not_found_handler,
    validation_error_handler,
)
from private_legal_navigator.api.routes import router as case_router
from private_legal_navigator.config import Settings
from private_legal_navigator.infrastructure.local_file_storage import LocalFileStorage
from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor
from private_legal_navigator.infrastructure.rule_based_classifier import RuleBasedClassifier
from private_legal_navigator.infrastructure.sqlite_case_repository import (
    SqliteCaseRepository,
)
from private_legal_navigator.infrastructure.sqlite_document_repository import (
    SqliteDocumentRepository,
)


def _document_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "DOCUMENT_NOT_FOUND",
                "message": "Das angeforderte Dokument wurde nicht gefunden.",
            }
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: ensure database directory and schema."""
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    repo: SqliteCaseRepository = app.state.case_repository
    repo.initialize_schema()
    doc_repo: SqliteDocumentRepository = app.state.document_repository
    doc_repo.initialize_schema()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    # Ensure directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = settings.data_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Initialize repositories and storage
    case_repository = SqliteCaseRepository(settings.database_path)
    case_repository.initialize_schema()
    document_repository = SqliteDocumentRepository(settings.database_path)
    document_repository.initialize_schema()
    file_storage = LocalFileStorage(docs_dir)
    text_extractor = PdfTextExtractor()
    classifier = RuleBasedClassifier()

    app = FastAPI(
        title="PrivateLegalNavigator",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Store in app state for dependency injection
    app.state.settings = settings
    app.state.case_repository = case_repository
    app.state.document_repository = document_repository
    app.state.file_storage = file_storage
    app.state.text_extractor = text_extractor
    app.state.classifier = classifier

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(CaseNotFoundError, case_not_found_handler)
    app.add_exception_handler(DocumentNotFoundError, _document_not_found_handler)

    # Register routes
    app.include_router(case_router)
    app.include_router(document_router)

    # Health check
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

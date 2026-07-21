"""FastAPI application factory and lifecycle management."""

import logging as _logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from private_legal_navigator.api.document_routes import router as document_router
from private_legal_navigator.api.errors import (
    CaseNotFoundError,
    DocumentNotFoundError,
    case_not_found_handler,
    validation_error_handler,
)
from private_legal_navigator.api.reference_event_routes import router as reference_event_router
from private_legal_navigator.api.routes import router as case_router
from private_legal_navigator.api.ui_routes import router as ui_router
from private_legal_navigator.application.calculation_service import CalculationService
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.local_confirmation_workspace_service import (
    LocalConfirmationWorkspaceService,
)
from private_legal_navigator.application.reference_event_service import (
    ReferenceEventService,
)
from private_legal_navigator.config import Settings
from private_legal_navigator.infrastructure.deterministic_calendar_arithmetic import (
    DeterministicCalendarArithmetic,
)
from private_legal_navigator.infrastructure.deterministic_deadline_extractor import (
    DeterministicDeadlineExtractor,
)
from private_legal_navigator.infrastructure.local_file_storage import LocalFileStorage
from private_legal_navigator.infrastructure.log_redaction import configure_logging
from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor
from private_legal_navigator.infrastructure.rule_based_classifier import RuleBasedClassifier
from private_legal_navigator.infrastructure.safe_logging import safe_log_failure
from private_legal_navigator.infrastructure.sqlite_case_repository import (
    SqliteCaseRepository,
)
from private_legal_navigator.infrastructure.sqlite_document_repository import (
    SqliteDocumentRepository,
)
from private_legal_navigator.infrastructure.sqlite_reference_event_repository import (
    SqliteReferenceEventRepository,
)
from private_legal_navigator.middleware.csrf import CsrfConfig, CsrfTokenService
from private_legal_navigator.middleware.host_validation import HostValidationMiddleware
from private_legal_navigator.middleware.security_headers import SecurityHeadersMiddleware


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
    # Initialize M6-A schema (idempotent)
    ref_repo: SqliteReferenceEventRepository = app.state.reference_event_repository
    ref_repo.initialize_schema()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    # Configure logging with privacy redaction (must happen first)
    configure_logging()

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
    deadline_extractor = DeterministicDeadlineExtractor()
    reference_event_repository = SqliteReferenceEventRepository(settings.database_path)
    calendar_arithmetic = DeterministicCalendarArithmetic()
    reference_event_service = ReferenceEventService(
        repo=reference_event_repository,
        secret_key=settings.csrf_secret,
    )
    calculation_service = CalculationService(
        repo=reference_event_repository,
        arithmetic=calendar_arithmetic,
    )

    # --- M6-UI: CSRF token service ---
    csrf_service = CsrfTokenService(
        CsrfConfig(secret=settings.csrf_secret, token_lifetime_seconds=3600)
    )

    app = FastAPI(
        title="PrivateLegalNavigator",
        version="0.2.0",
        lifespan=lifespan,
    )

    # --- M6-UI: Templates and services ---
    templates = Jinja2Templates(directory=str(settings.template_dir))
    workspace_service = LocalConfirmationWorkspaceService(
        case_repository=case_repository,
        document_repository=document_repository,
        document_service=DocumentService(
            document_repository,
            file_storage,
            case_repository,
            text_extractor,
            classifier,
        ),
        deadline_service=DeadlineService(
            document_repository,
            deadline_extractor,
        ),
        reference_event_service=reference_event_service,
        csrf_service=csrf_service,
        calendar_arithmetic=calendar_arithmetic,
    )

    # --- M6-UI: Middleware ---
    # Order: HostValidation (outermost user middleware) → SecurityHeaders
    app.add_middleware(
        HostValidationMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    app.add_middleware(SecurityHeadersMiddleware)

    # --- M6-UI: Static files ---
    static_dir = str(settings.static_dir)
    if Path(static_dir).is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Store in app state for dependency injection
    app.state.settings = settings
    app.state.case_repository = case_repository
    app.state.document_repository = document_repository
    app.state.file_storage = file_storage
    app.state.text_extractor = text_extractor
    app.state.classifier = classifier
    app.state.deadline_extractor = deadline_extractor
    app.state.reference_event_repository = reference_event_repository
    app.state.calendar_arithmetic = calendar_arithmetic
    app.state.reference_event_service = reference_event_service
    app.state.calculation_service = calculation_service
    app.state.templates = templates
    app.state.workspace_service = workspace_service
    app.state.csrf_service = csrf_service

    # Initialize M6-A schema
    reference_event_repository.initialize_schema()

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(CaseNotFoundError, case_not_found_handler)
    app.add_exception_handler(DocumentNotFoundError, _document_not_found_handler)

    # Catch-all exception boundary: prevents raw tracebacks and exception
    # messages from reaching Uvicorn's error log. Logs ONLY a stable error
    # code and the exception type name, never the exception message.
    app_logger = _logging.getLogger("private_legal_navigator")

    @app.exception_handler(Exception)
    async def _catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
        safe_log_failure(
            app_logger,
            "application.unhandled_error",
            error_code="INTERNAL_PROCESSING_ERROR",
            exception=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_PROCESSING_ERROR",
                    "message": "Der Vorgang konnte nicht abgeschlossen werden.",
                }
            },
        )

    # Register routes
    app.include_router(case_router)
    app.include_router(document_router)
    app.include_router(reference_event_router)
    app.include_router(ui_router)

    # Health check
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

"""FastAPI route definitions for Document upload and retrieval."""

import uuid

from fastapi import APIRouter, Depends, Request, UploadFile, status
from fastapi.responses import Response

from private_legal_navigator.api.deadline_schemas import (
    DeadlineCandidateResponse,
    DeadlineExtractionResponse,
    DeadlineWarningResponse,
)
from private_legal_navigator.api.errors import CaseNotFoundError, DocumentNotFoundError
from private_legal_navigator.api.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentTextResponse,
)
from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.deadline_extractor import DeadlineExtractor
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.application.document_classifier import DocumentClassifier
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.file_storage import FileStorage
from private_legal_navigator.application.text_extractor import TextExtractor
from private_legal_navigator.domain.deadline import (
    DeadlineCandidate,
    DeadlineWarning,
)
from private_legal_navigator.domain.document import Document

router = APIRouter(prefix="/api/v1/cases", tags=["documents"])


def get_case_repository(request: Request) -> CaseRepository:
    repo = request.app.state.case_repository
    assert isinstance(repo, CaseRepository)
    return repo


def get_document_repository(request: Request) -> DocumentRepository:
    repo = request.app.state.document_repository
    assert isinstance(repo, DocumentRepository)
    return repo


def get_file_storage(request: Request) -> FileStorage:
    storage = request.app.state.file_storage
    assert isinstance(storage, FileStorage)
    return storage


def get_text_extractor(request: Request) -> TextExtractor:
    extractor = request.app.state.text_extractor
    assert isinstance(extractor, TextExtractor)
    return extractor


def get_classifier(request: Request) -> DocumentClassifier:
    classifier = request.app.state.classifier
    assert isinstance(classifier, DocumentClassifier)
    return classifier


def get_deadline_extractor(request: Request) -> DeadlineExtractor:
    extractor = request.app.state.deadline_extractor
    assert isinstance(extractor, DeadlineExtractor)
    return extractor


def get_document_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),  # noqa: B008
    file_storage: FileStorage = Depends(get_file_storage),  # noqa: B008
    case_repo: CaseRepository = Depends(get_case_repository),  # noqa: B008
    text_extractor: TextExtractor = Depends(get_text_extractor),  # noqa: B008
    classifier: DocumentClassifier = Depends(get_classifier),  # noqa: B008
) -> DocumentService:
    return DocumentService(doc_repo, file_storage, case_repo, text_extractor, classifier)


def get_deadline_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),  # noqa: B008
    deadline_extractor: DeadlineExtractor = Depends(get_deadline_extractor),  # noqa: B008
) -> DeadlineService:
    return DeadlineService(doc_repo, deadline_extractor)


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        document_id=doc.document_id,
        case_id=doc.case_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at,
        doc_type=doc.doc_type,
        classification_confidence=doc.classification_confidence,
    )


@router.post(
    "/{case_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
)
async def upload_document(
    case_id: uuid.UUID,
    file: UploadFile,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentResponse:
    """Upload a PDF document to a case."""
    if not file.filename:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Kein Dateiname."}},
        )

    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    try:
        doc = service.upload_document(
            case_id=case_id,
            filename=file.filename,
            content=content,
            mime_type=mime_type,
            size_bytes=len(content),
        )
    except ValueError as e:
        msg = str(e)
        if "nicht gefunden" in msg:
            raise CaseNotFoundError() from e
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_ERROR", "message": msg}},
        ) from e

    return _doc_to_response(doc)


@router.get(
    "/{case_id}/documents",
    response_model=DocumentListResponse,
)
def list_documents(
    case_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentListResponse:
    """List all documents for a case."""
    docs = service.list_case_documents(case_id)
    return DocumentListResponse(
        items=[_doc_to_response(d) for d in docs],
        count=len(docs),
    )


@router.get("/{case_id}/documents/{document_id}")
async def get_document(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> Response:
    """Download a document."""
    result = service.get_document(document_id)
    if result is None:
        raise DocumentNotFoundError()

    doc, content = result
    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.filename}"',
        },
    )


@router.get(
    "/{case_id}/documents/{document_id}/text",
    response_model=DocumentTextResponse,
)
def get_document_text(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentTextResponse:
    """Get extracted text for a document."""
    doc = service.get_document_text(document_id)
    if doc is None:
        raise DocumentNotFoundError()
    return DocumentTextResponse(
        document_id=doc.document_id,
        text_content=doc.text_content,
        text_length=len(doc.text_content),
    )


# ---------------------------------------------------------------------------
# M5: Deadline Candidate Extraction
# ---------------------------------------------------------------------------


def _deadline_candidate_to_response(c: DeadlineCandidate) -> DeadlineCandidateResponse:
    from private_legal_navigator.api.deadline_schemas import (
        DeadlineCandidateKindSchema,
        DeadlineCertaintySchema,
    )

    return DeadlineCandidateResponse(
        kind=DeadlineCandidateKindSchema(c.kind.value),
        raw_text=c.raw_text,
        start_offset=c.start_offset,
        end_offset=c.end_offset,
        normalized_date=c.normalized_date,
        amount=c.amount,
        unit=c.unit,
        reference_required=c.reference_required,
        certainty=DeadlineCertaintySchema(c.certainty.value),
        rule_id=c.rule_id,
    )


def _deadline_warning_to_response(w: DeadlineWarning) -> DeadlineWarningResponse:
    from private_legal_navigator.api.deadline_schemas import (
        DeadlineWarningCodeSchema,
    )

    return DeadlineWarningResponse(
        code=DeadlineWarningCodeSchema(w.code.value),
        message=w.message,
    )


@router.post(
    "/{case_id}/documents/{document_id}/deadline-candidates",
    response_model=DeadlineExtractionResponse,
)
def extract_deadline_candidates(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DeadlineService = Depends(get_deadline_service),  # noqa: B008
) -> DeadlineExtractionResponse:
    """Extract deadline candidates from a document's text.

    Erkennt deterministisch mögliche Frist- und Terminangaben.
    Berechnet KEINE verbindliche Rechtsfrist.
    """
    from private_legal_navigator.infrastructure.deterministic_deadline_extractor import (
        ExtractionTimeoutError,
        TextTooLargeError,
    )

    try:
        result = service.extract_candidates(document_id)
    except TextTooLargeError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=413,
            detail={"error": {"code": "TEXT_TOO_LARGE", "message": str(e)}},
        ) from e
    except ExtractionTimeoutError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "EXTRACTION_TIMEOUT", "message": str(e)}},
        ) from e

    if result is None:
        raise DocumentNotFoundError()

    return DeadlineExtractionResponse(
        document_id=uuid.UUID(result.document_id),
        candidates=[_deadline_candidate_to_response(c) for c in result.candidates],
        warnings=[_deadline_warning_to_response(w) for w in result.warnings],
        human_review_required=result.human_review_required,
    )

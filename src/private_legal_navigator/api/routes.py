"""FastAPI route definitions for the Case API."""

import uuid

from fastapi import APIRouter, Depends, Request, status

from private_legal_navigator.api.errors import CaseNotFoundError
from private_legal_navigator.api.schemas import (
    CaseListResponse,
    CaseResponse,
    CreateCaseRequest,
)
from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.case_service import CaseService
from private_legal_navigator.domain.case import Case

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def get_repository(request: Request) -> CaseRepository:
    """Dependency: provide the CaseRepository from app state."""
    repo = request.app.state.repository
    assert isinstance(repo, CaseRepository)
    return repo


def get_case_service(
    repository: CaseRepository = Depends(get_repository),  # noqa: B008
) -> CaseService:
    """Dependency: provide a CaseService wired to the current app's repository."""
    return CaseService(repository)


def _case_to_response(case: Case) -> CaseResponse:
    """Map a domain Case entity to an API response model."""
    return CaseResponse(
        case_id=case.case_id,
        title=case.title,
        status=case.status.value,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CaseResponse)
def create_case(
    request: CreateCaseRequest,
    service: CaseService = Depends(get_case_service),  # noqa: B008
) -> CaseResponse:
    """Create a new case."""
    case = service.create_case(title=request.title)
    return _case_to_response(case)


@router.get("", response_model=CaseListResponse)
def list_cases(
    service: CaseService = Depends(get_case_service),  # noqa: B008
) -> CaseListResponse:
    """List all cases."""
    cases = service.list_cases()
    return CaseListResponse(
        items=[_case_to_response(c) for c in cases],
        count=len(cases),
    )


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: uuid.UUID,
    service: CaseService = Depends(get_case_service),  # noqa: B008
) -> CaseResponse:
    """Get a single case by ID."""
    case = service.get_case(case_id)
    if case is None:
        raise CaseNotFoundError()
    return _case_to_response(case)

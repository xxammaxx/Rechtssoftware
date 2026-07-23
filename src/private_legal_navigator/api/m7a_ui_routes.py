"""M7-A legal source and case timeline web UI routes.

All mutations are POST-only with CSRF protection.
Case/provision ownership is verified server-side.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from private_legal_navigator.domain.case_timeline import LegalEventType


router = APIRouter(prefix="/ui", tags=["m7a-ui"])


def _get_services(request: Request) -> dict[str, Any]:
    """Extract all needed services from app state."""
    return {
        "templates": request.app.state.templates,
        "legal_source": request.app.state.legal_source_service,
        "timeline": request.app.state.case_timeline_service,
        "csrf": request.app.state.csrf_service,
        "legal_repo": request.app.state.legal_source_repository,
        "case_repo": request.app.state.case_repository,
    }


def _get_case_or_404(request: Request, case_id: str) -> tuple[Any, dict[str, Any]]:
    """Get case entity or raise 404."""
    svc = _get_services(request)
    case = svc["case_repo"].get_by_id(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return case, svc


# ═══════════════════════════════════════════════════════
# Legal Source Status
# ═══════════════════════════════════════════════════════


@router.get("/legal-sources", response_class=HTMLResponse)
async def legal_source_status(request: Request) -> Any:
    """Show legal source status overview."""
    svc = _get_services(request)
    status_list = svc["legal_source"].get_source_status()
    csrf_token = svc["csrf"].create_token(str(uuid.uuid4()))

    # Enrich with snapshot count
    for s in status_list:
        key = s["source_key"]
        snaps = (
            svc["legal_repo"].list_snapshots_for_source(key)
            if hasattr(svc["legal_repo"], "list_snapshots_for_source")
            else []
        )
        s["snapshot_count"] = len(snaps)

    return svc["templates"].TemplateResponse(
        "m7a/legal_sources.html",
        {
            "request": request,
            "base": {"page_title": "Rechtsquellen"},
            "sources": status_list,
            "csrf_token": csrf_token,
        },
    )


# ═══════════════════════════════════════════════════════
# Legal Source Search
# ═══════════════════════════════════════════════════════


@router.get("/legal-sources/search", response_class=HTMLResponse)
async def legal_source_search_get(request: Request, q: str = "") -> Any:
    """Search legal sources."""
    svc = _get_services(request)
    csrf_token = svc["csrf"].create_token(str(uuid.uuid4()))
    results = []
    query = q.strip()

    if query:
        results = svc["legal_source"].search(query, limit=50)

    return svc["templates"].TemplateResponse(
        "m7a/legal_sources_search.html",
        {
            "request": request,
            "base": {"page_title": "Rechtsquellensuche"},
            "csrf_token": csrf_token,
            "query": query,
            "results": results,
        },
    )


# ═══════════════════════════════════════════════════════
# Norm Detail
# ═══════════════════════════════════════════════════════


@router.get("/legal-sources/norm/{provision_id}", response_class=HTMLResponse)
async def norm_detail(request: Request, provision_id: str) -> Any:
    """Show detailed view of a specific legal provision (norm)."""
    svc = _get_services(request)
    csrf_token = svc["csrf"].create_token(str(uuid.uuid4()))

    try:
        pid = uuid.UUID(provision_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail="Ungültige Norm-ID") from err

    provision = svc["legal_repo"].get_provision(pid)
    if provision is None:
        raise HTTPException(status_code=404, detail="Norm nicht gefunden")

    assert provision.expression_id is not None
    expression = svc["legal_repo"].get_expression(provision.expression_id)
    instrument = None
    snapshot = None
    if expression is not None:
        assert expression.instrument_id is not None
        instrument = svc["legal_repo"].get_instrument(expression.instrument_id)
        if expression.source_snapshot_id:
            snapshot = svc["legal_repo"].get_snapshot(expression.source_snapshot_id)

    return svc["templates"].TemplateResponse(
        "m7a/norm_detail.html",
        {
            "request": request,
            "base": {"page_title": f"§ {provision.provision_number} — Normdetail"},
            "csrf_token": csrf_token,
            "provision": provision,
            "expression": expression,
            "instrument": instrument,
            "snapshot": snapshot,
        },
    )


# ═══════════════════════════════════════════════════════
# Case: Legal Situation (Rechtslage)
# ═══════════════════════════════════════════════════════


@router.get("/cases/{case_id}/legal-situation", response_class=HTMLResponse)
async def case_legal_situation(request: Request, case_id: str) -> Any:
    """Show legal situation (Rechtslage) for a case."""
    case, svc = _get_case_or_404(request, case_id)
    csrf_token = svc["csrf"].create_token(case_id)

    links = svc["timeline"].list_links(case_id)
    active_links = svc["timeline"].list_active_links(case_id)

    return svc["templates"].TemplateResponse(
        "m7a/case_legal_situation.html",
        {
            "request": request,
            "base": {"page_title": f"{case.title} — Rechtslage"},
            "csrf_token": csrf_token,
            "case": case,
            "case_id": case_id,
            "links": links,
            "active_links": active_links,
        },
    )


@router.post("/cases/{case_id}/legal-situation/link", response_class=HTMLResponse)
async def create_norm_link(
    request: Request,
    case_id: str,
    provision_id: str = Form(...),
    relevance_note: str = Form(""),
    csrf_token: str = Form(...),
) -> Any:
    """Create a candidate norm link for a case."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].link_provision_to_case(
            case_id=case_id,
            provision_id=uuid.UUID(provision_id),
            relevance_note=relevance_note,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-situation", status_code=303)


@router.post("/cases/{case_id}/legal-situation/confirm", response_class=HTMLResponse)
async def confirm_norm_link(
    request: Request,
    case_id: str,
    link_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Confirm a norm link."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].confirm_link(link_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-situation", status_code=303)


@router.post("/cases/{case_id}/legal-situation/reject", response_class=HTMLResponse)
async def reject_norm_link(
    request: Request,
    case_id: str,
    link_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Reject a norm link."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].reject_link(link_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-situation", status_code=303)


@router.post("/cases/{case_id}/legal-situation/correct", response_class=HTMLResponse)
async def correct_norm_link(
    request: Request,
    case_id: str,
    link_id: str = Form(...),
    new_provision_id: str = Form(...),
    new_relevance_note: str = Form(""),
    csrf_token: str = Form(...),
) -> Any:
    """Correct a norm link (creates new version, keeps history)."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].correct_link(
            link_id=link_id,
            new_provision_id=uuid.UUID(new_provision_id),
            new_relevance_note=new_relevance_note,
        )
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-situation", status_code=303)


@router.post("/cases/{case_id}/legal-situation/revoke", response_class=HTMLResponse)
async def revoke_norm_link(
    request: Request,
    case_id: str,
    link_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Revoke a norm link."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].revoke_link(link_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-situation", status_code=303)


# ═══════════════════════════════════════════════════════
# Case: Legal Timeline (Rechtsverlauf)
# ═══════════════════════════════════════════════════════


@router.get("/cases/{case_id}/legal-timeline", response_class=HTMLResponse)
async def case_legal_timeline(request: Request, case_id: str) -> Any:
    """Show legal timeline (Rechtsverlauf) for a case."""
    case, svc = _get_case_or_404(request, case_id)
    csrf_token = svc["csrf"].create_token(case_id)

    events = svc["timeline"].list_events(case_id)
    active_events = svc["timeline"].list_active_events(case_id)

    return svc["templates"].TemplateResponse(
        "m7a/case_legal_timeline.html",
        {
            "request": request,
            "base": {"page_title": f"{case.title} — Rechtsverlauf"},
            "csrf_token": csrf_token,
            "case": case,
            "case_id": case_id,
            "events": events,
            "active_events": active_events,
        },
    )


@router.post("/cases/{case_id}/legal-timeline/event", response_class=HTMLResponse)
async def create_legal_event(
    request: Request,
    case_id: str,
    event_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    occurred_at: str = Form(""),
    known_at: str = Form(""),
    source_document_id: str = Form(""),
    csrf_token: str = Form(...),
) -> Any:
    """Create a legal event for a case."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].create_event(
            case_id=case_id,
            event_type=LegalEventType(event_type),
            title=title,
            description=description,
            occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else None,
            known_at=datetime.fromisoformat(known_at) if known_at else None,
            source_document_id=source_document_id or None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-timeline", status_code=303)


@router.post("/cases/{case_id}/legal-timeline/confirm", response_class=HTMLResponse)
async def confirm_legal_event(
    request: Request,
    case_id: str,
    event_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Confirm a legal event."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].confirm_event(event_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-timeline", status_code=303)


@router.post("/cases/{case_id}/legal-timeline/reject", response_class=HTMLResponse)
async def reject_legal_event(
    request: Request,
    case_id: str,
    event_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Reject a legal event."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].reject_event(event_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-timeline", status_code=303)


@router.post("/cases/{case_id}/legal-timeline/correct", response_class=HTMLResponse)
async def correct_legal_event(
    request: Request,
    case_id: str,
    event_id: str = Form(...),
    new_title: str = Form(...),
    new_description: str = Form(""),
    new_event_type: str = Form(""),
    new_occurred_at: str = Form(""),
    new_known_at: str = Form(""),
    csrf_token: str = Form(...),
) -> Any:
    """Correct a legal event (creates new version, keeps history)."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].correct_event(
            event_id=event_id,
            new_title=new_title,
            new_description=new_description,
            new_event_type=LegalEventType(new_event_type) if new_event_type else None,
            new_occurred_at=(datetime.fromisoformat(new_occurred_at) if new_occurred_at else None),
            new_known_at=(datetime.fromisoformat(new_known_at) if new_known_at else None),
        )
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-timeline", status_code=303)


@router.post("/cases/{case_id}/legal-timeline/revoke", response_class=HTMLResponse)
async def revoke_legal_event(
    request: Request,
    case_id: str,
    event_id: str = Form(...),
    csrf_token: str = Form(...),
) -> Any:
    """Revoke a legal event."""
    case, svc = _get_case_or_404(request, case_id)
    svc["csrf"].validate(csrf_token, case_id)

    try:
        svc["timeline"].revoke_event(event_id)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    return RedirectResponse(f"/ui/cases/{case_id}/legal-timeline", status_code=303)


# ═══════════════════════════════════════════════════════
# Evidence Pack Export
# ═══════════════════════════════════════════════════════


@router.get("/cases/{case_id}/evidence-pack", response_class=HTMLResponse)
async def evidence_pack(request: Request, case_id: str) -> Any:
    """Show evidence pack export for a case (read-only preview)."""
    case, svc = _get_case_or_404(request, case_id)
    csrf_token = svc["csrf"].create_token(case_id)

    pack = svc["timeline"].build_evidence_pack(case_id)

    return svc["templates"].TemplateResponse(
        "m7a/evidence_pack.html",
        {
            "request": request,
            "base": {"page_title": f"{case.title} — Evidence Pack"},
            "csrf_token": csrf_token,
            "case": case,
            "case_id": case_id,
            "pack": pack,
        },
    )


# ═══════════════════════════════════════════════════════
# Error pages
# ═══════════════════════════════════════════════════════


@router.get("/errors/400", response_class=HTMLResponse)
async def error_400(request: Request) -> Any:
    svc = _get_services(request)
    return svc["templates"].TemplateResponse(
        "m7a/error.html",
        {
            "request": request,
            "base": {"page_title": "Fehler"},
            "error_code": 400,
            "error_message": "Ungültige Anfrage.",
        },
        status_code=400,
    )


@router.get("/errors/403", response_class=HTMLResponse)
async def error_403(request: Request) -> Any:
    svc = _get_services(request)
    return svc["templates"].TemplateResponse(
        "m7a/error.html",
        {
            "request": request,
            "base": {"page_title": "Fehler"},
            "error_code": 403,
            "error_message": "Zugriff verweigert.",
        },
        status_code=403,
    )


@router.get("/errors/404", response_class=HTMLResponse)
async def error_404(request: Request) -> Any:
    svc = _get_services(request)
    return svc["templates"].TemplateResponse(
        "m7a/error.html",
        {
            "request": request,
            "base": {"page_title": "Fehler"},
            "error_code": 404,
            "error_message": "Seite nicht gefunden.",
        },
        status_code=404,
    )


@router.get("/errors/409", response_class=HTMLResponse)
async def error_409(request: Request) -> Any:
    svc = _get_services(request)
    return svc["templates"].TemplateResponse(
        "m7a/error.html",
        {
            "request": request,
            "base": {"page_title": "Fehler"},
            "error_code": 409,
            "error_message": (
                "Konflikt bei der Operation. Möglicherweise wurde der Datensatz bereits geändert."
            ),
        },
        status_code=409,
    )

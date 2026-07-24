"""Case legal timeline application service (M7-A).

Orchestrates legal event and link operations for a case.
All state changes go through human review (CANDIDATE → CONFIRMED/REJECTED/REVOKED).
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from private_legal_navigator.domain.case_timeline import (
    CaseLegalEvent,
    CaseLegalLink,
    EvidencePack,
    LegalEventType,
    LegalLinkStatus,
    ReviewStatus,
)
from private_legal_navigator.infrastructure.sqlite_case_timeline_repository import (
    SqliteCaseTimelineRepository,
)
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)

logger = logging.getLogger("private_legal_navigator.case_timeline")


class CaseTimelineService:
    """Application service for case legal timeline and norm links."""

    def __init__(
        self,
        timeline_repo: SqliteCaseTimelineRepository,
        legal_repo: SqliteLegalSourceRepository,
    ) -> None:
        self._timeline_repo = timeline_repo
        self._legal_repo = legal_repo

    # ── Event Management ────────────────────────

    def create_event(
        self,
        case_id: uuid.UUID,
        event_type: LegalEventType,
        *,
        title: str = "",
        description: str = "",
        occurred_at: datetime | None = None,
        known_at: datetime | None = None,
        source_document_id: str | None = None,
    ) -> CaseLegalEvent:
        """Create a legal event (route-compatible wrapper for add_event_candidate)."""
        return self.add_event_candidate(
            case_id=case_id,
            event_type=event_type,
            title=title,
            description=description,
            occurred_at=occurred_at,
            known_at=known_at,
            source_document_id=(uuid.UUID(source_document_id) if source_document_id else None),
        )

    def list_events(self, case_id: uuid.UUID) -> list[CaseLegalEvent]:
        """List all legal events for a case."""
        return self._timeline_repo.list_events(case_id)

    def list_active_events(self, case_id: uuid.UUID) -> list[CaseLegalEvent]:
        """List active (confirmed, non-revoked) events for a case."""
        return self._timeline_repo.list_active_events(case_id)

    def add_event_candidate(
        self,
        case_id: uuid.UUID,
        event_type: LegalEventType,
        *,
        title: str = "",
        description: str = "",
        occurred_at: datetime | None = None,
        known_at: datetime | None = None,
        source_document_id: uuid.UUID | None = None,
        actor: str = "",
        amount: str = "",
    ) -> CaseLegalEvent:
        """Add a legal event as a CANDIDATE (requires human confirmation)."""
        event = CaseLegalEvent(
            event_id=uuid.uuid4(),
            case_id=case_id,
            event_type=event_type,
            occurred_at=occurred_at,
            known_at=known_at,
            recorded_at=datetime.now(),
            title=title,
            description=description,
            source_document_id=source_document_id,
            review_status=ReviewStatus.CANDIDATE,
            actor=actor,
            amount=amount,
        )
        self._timeline_repo.save_event(event)
        return event

    def confirm_event(self, event_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalEvent:
        """Confirm a candidate legal event."""
        event = self._require_event(event_id, case_id)
        if event.review_status != ReviewStatus.CANDIDATE:
            raise ValueError(f"Event {event_id} is not in CANDIDATE status")
        event.review_status = ReviewStatus.CONFIRMED
        self._timeline_repo.save_event(event)
        return event

    def reject_event(self, event_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalEvent:
        """Reject a candidate legal event."""
        event = self._require_event(event_id, case_id)
        if event.review_status != ReviewStatus.CANDIDATE:
            raise ValueError(f"Event {event_id} is not in CANDIDATE status")
        event.review_status = ReviewStatus.REJECTED
        self._timeline_repo.save_event(event)
        return event

    def correct_event(
        self,
        event_id: uuid.UUID,
        *,
        case_id: uuid.UUID,
        new_title: str = "",
        new_description: str = "",
        new_event_type: LegalEventType | None = None,
        new_occurred_at: datetime | None = None,
        new_known_at: datetime | None = None,
    ) -> CaseLegalEvent:
        """Correct an event (route-compatible wrapper)."""
        self._require_event(event_id, case_id)  # Validate cross-case ownership
        updates: dict[str, Any] = {}
        if new_title:
            updates["title"] = new_title
        if new_description:
            updates["description"] = new_description
        if new_event_type is not None:
            updates["event_type"] = new_event_type
        if new_occurred_at is not None:
            updates["occurred_at"] = new_occurred_at
        if new_known_at is not None:
            updates["known_at"] = new_known_at
        return self._correct_event_impl(event_id, **updates)

    def _correct_event_impl(
        self,
        event_id: uuid.UUID,
        **updates: Any,
    ) -> CaseLegalEvent:
        """Correct an existing legal event (creates new version, preserves old)."""
        original = self._require_event(event_id)
        if original.review_status not in (ReviewStatus.CONFIRMED, ReviewStatus.CORRECTED):
            raise ValueError(
                f"Event {event_id} cannot be corrected (must be CONFIRMED or CORRECTED)"
            )

        # Create corrected version
        corrected = CaseLegalEvent(
            event_id=uuid.uuid4(),
            case_id=original.case_id,
            event_type=LegalEventType(updates.get("event_type", original.event_type.value)),
            occurred_at=(
                updates.get("occurred_at") if "occurred_at" in updates else original.occurred_at
            )
            or original.occurred_at,
            known_at=updates.get("known_at", original.known_at) or original.known_at,
            recorded_at=datetime.now(),
            title=updates.get("title", original.title) or original.title,
            description=updates.get("description", original.description) or original.description,
            source_document_id=original.source_document_id,
            review_status=ReviewStatus.CORRECTED,
            previous_event_id=original.event_id,
            actor=updates.get("actor", original.actor) or original.actor,
            amount=updates.get("amount", original.amount) or original.amount,
        )
        self._timeline_repo.save_event(corrected)

        # Mark original as SUPERSEDED
        original.review_status = ReviewStatus.SUPERSEDED
        self._timeline_repo.save_event(original)

        return corrected

    def revoke_event(self, event_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalEvent:
        """Revoke a legal event (preserves record, sets revoked_at)."""
        event = self._require_event(event_id, case_id)
        if event.review_status not in (ReviewStatus.CONFIRMED, ReviewStatus.CORRECTED):
            raise ValueError(f"Event {event_id} cannot be revoked (must be CONFIRMED or CORRECTED)")
        event.review_status = ReviewStatus.REVOKED
        event.revoked_at = datetime.now()
        self._timeline_repo.save_event(event)
        return event

    def get_timeline(self, case_id: uuid.UUID) -> list[CaseLegalEvent]:
        """Get the active timeline for a case (confirmed, non-revoked events)."""
        return self._timeline_repo.list_active_events(case_id)

    def get_event_history(self, case_id: uuid.UUID, event_id: uuid.UUID) -> list[CaseLegalEvent]:
        """Get the full version history of an event."""
        return self._timeline_repo.get_event_history(case_id, event_id)

    # ── Link Management ─────────────────────────

    def list_links(self, case_id: uuid.UUID) -> list[CaseLegalLink]:
        """List all legal links for a case."""
        return self._timeline_repo.list_links(case_id)

    def link_provision_to_case(
        self,
        case_id: uuid.UUID,
        provision_id: uuid.UUID,
        *,
        relevance_note: str = "",
    ) -> CaseLegalLink:
        """Create a norm-to-case link (route-compatible wrapper for propose_link)."""
        return self.propose_link(
            case_id=case_id,
            legal_provision_id=provision_id,
            relevance_note=relevance_note,
        )

    def propose_link(
        self,
        case_id: uuid.UUID,
        legal_provision_id: uuid.UUID,
        *,
        document_id: uuid.UUID | None = None,
        relevance_note: str = "",
    ) -> CaseLegalLink:
        """Propose a norm-to-case link as CANDIDATE."""
        # Verify the provision exists
        provision = self._legal_repo.get_provision(legal_provision_id)
        if provision is None:
            raise ValueError(f"Legal provision not found: {legal_provision_id}")

        link = CaseLegalLink(
            link_id=uuid.uuid4(),
            case_id=case_id,
            document_id=document_id,
            legal_provision_id=legal_provision_id,
            relevance_note=relevance_note,
            status=LegalLinkStatus.CANDIDATE,
        )
        self._timeline_repo.save_link(link)
        return link

    def confirm_link(self, link_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalLink:
        """Confirm a candidate link."""
        link = self._require_link(link_id, case_id)
        if link.status != LegalLinkStatus.CANDIDATE:
            raise ValueError(f"Link {link_id} is not in CANDIDATE status")
        link.status = LegalLinkStatus.CONFIRMED
        link.confirmed_at = datetime.now()
        self._timeline_repo.save_link(link)
        return link

    def reject_link(self, link_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalLink:
        """Reject a candidate link."""
        link = self._require_link(link_id, case_id)
        if link.status != LegalLinkStatus.CANDIDATE:
            raise ValueError(f"Link {link_id} is not in CANDIDATE status")
        link.status = LegalLinkStatus.REJECTED
        self._timeline_repo.save_link(link)
        return link

    def correct_link(
        self,
        link_id: uuid.UUID,
        *,
        case_id: uuid.UUID,
        new_provision_id: uuid.UUID | None = None,
        new_relevance_note: str = "",
    ) -> CaseLegalLink:
        """Correct a link (route-compatible wrapper)."""
        self._require_link(link_id, case_id)  # Validate cross-case ownership
        return self._correct_link_impl(
            link_id=link_id,
            provision_id=new_provision_id,
            relevance_note=new_relevance_note,
        )

    def _correct_link_impl(
        self, link_id: uuid.UUID, *, relevance_note: str = "", provision_id: uuid.UUID | None = None
    ) -> CaseLegalLink:
        """Correct a link (creates new version, preserves old)."""
        original = self._require_link(link_id)
        if original.status not in (LegalLinkStatus.CONFIRMED, LegalLinkStatus.CORRECTED):
            raise ValueError(f"Link {link_id} cannot be corrected")

        corrected = CaseLegalLink(
            link_id=uuid.uuid4(),
            case_id=original.case_id,
            document_id=original.document_id,
            legal_provision_id=provision_id or original.legal_provision_id,
            relevance_note=relevance_note or original.relevance_note,
            status=LegalLinkStatus.CORRECTED,
            previous_link_id=original.link_id,
        )
        self._timeline_repo.save_link(corrected)

        original.status = LegalLinkStatus.SUPERSEDED
        self._timeline_repo.save_link(original)

        return corrected

    def revoke_link(self, link_id: uuid.UUID, *, case_id: uuid.UUID) -> CaseLegalLink:
        """Revoke a link (preserves record)."""
        link = self._require_link(link_id, case_id)
        if link.status not in (LegalLinkStatus.CONFIRMED, LegalLinkStatus.CORRECTED):
            raise ValueError(f"Link {link_id} cannot be revoked")
        link.status = LegalLinkStatus.REVOKED
        link.revoked_at = datetime.now()
        self._timeline_repo.save_link(link)
        return link

    def list_active_links(self, case_id: uuid.UUID) -> list[CaseLegalLink]:
        """List active (confirmed, non-revoked) links for a case."""
        return self._timeline_repo.list_active_links(case_id)

    # ── Evidence Pack ────────────────────────────

    def build_evidence_pack(self, case_id: uuid.UUID) -> EvidencePack:
        """Build a deterministic evidence pack for a case."""
        return self._timeline_repo.build_evidence_pack(case_id)

    def export_evidence_pack(self, case_id: uuid.UUID) -> dict[str, Any]:
        """Export evidence pack as JSON-serializable dict."""
        pack = self._timeline_repo.build_evidence_pack(case_id)
        return {
            "schema_version": pack.schema_version,
            "case_id": str(pack.case_id) if pack.case_id else None,
            "case_title": pack.case_title,
            "exported_at": pack.exported_at.isoformat() if pack.exported_at else None,
            "operating_mode": pack.operating_mode.value,
            "confirmed_facts": pack.confirmed_facts,
            "open_facts": pack.open_facts,
            "legal_events": pack.legal_events,
            "legal_issues": pack.legal_issues,
            "confirmed_legal_links": pack.confirmed_legal_links,
            "provisions": pack.provisions,
            "source_snapshots": pack.source_snapshots,
            "temporal_warnings": pack.temporal_warnings,
            "integrity": pack.integrity,
        }

    # ── Helpers ──────────────────────────────────

    def _require_event(
        self, event_id: uuid.UUID, case_id: uuid.UUID | str | None = None
    ) -> CaseLegalEvent:
        event = self._timeline_repo.get_event(event_id)
        if event is None:
            raise ValueError(f"Event not found: {event_id}")
        if case_id is not None:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
            if event.case_id != cid:
                raise ValueError(f"Event not found: {event_id}")
        return event

    def _require_link(
        self, link_id: uuid.UUID, case_id: uuid.UUID | str | None = None
    ) -> CaseLegalLink:
        link = self._timeline_repo.get_link(link_id)
        if link is None:
            raise ValueError(f"Link not found: {link_id}")
        if case_id is not None:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
            if link.case_id != cid:
                raise ValueError(f"Link not found: {link_id}")
        return link

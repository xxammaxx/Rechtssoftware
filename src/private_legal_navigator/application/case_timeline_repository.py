"""Repository port for case legal timeline operations (M7-A)."""

from abc import ABC, abstractmethod
from uuid import UUID

from private_legal_navigator.domain.case_timeline import (
    CaseLegalEvent,
    CaseLegalLink,
    EventRelation,
    EvidencePack,
    LegalIssue,
    ReviewStatus,
)


class CaseTimelineRepository(ABC):
    """Port for case legal timeline and legal link persistence."""

    # ── Events ───────────────────────────────────

    @abstractmethod
    def initialize_schema(self) -> None: ...
    @abstractmethod
    def save_event(self, event: CaseLegalEvent) -> None: ...
    @abstractmethod
    def get_event(self, event_id: UUID) -> CaseLegalEvent | None: ...
    @abstractmethod
    def list_events(
        self,
        case_id: UUID,
        *,
        status: ReviewStatus | None = None,
        include_revoked: bool = False,
    ) -> list[CaseLegalEvent]: ...
    @abstractmethod
    def list_active_events(self, case_id: UUID) -> list[CaseLegalEvent]: ...
    @abstractmethod
    def get_event_history(self, case_id: UUID, event_id: UUID) -> list[CaseLegalEvent]: ...

    # ── Relations ────────────────────────────────

    @abstractmethod
    def save_relation(self, relation: EventRelation) -> None: ...
    @abstractmethod
    def get_relations_for_event(self, event_id: UUID) -> list[EventRelation]: ...
    @abstractmethod
    def list_relations(self, case_id: UUID) -> list[EventRelation]: ...

    # ── Links ────────────────────────────────────

    @abstractmethod
    def save_link(self, link: CaseLegalLink) -> None: ...
    @abstractmethod
    def get_link(self, link_id: UUID) -> CaseLegalLink | None: ...
    @abstractmethod
    def list_links(
        self, case_id: UUID, *, include_revoked: bool = False
    ) -> list[CaseLegalLink]: ...
    @abstractmethod
    def list_active_links(self, case_id: UUID) -> list[CaseLegalLink]: ...
    @abstractmethod
    def get_link_history(self, case_id: UUID, link_id: UUID) -> list[CaseLegalLink]: ...

    # ── Issues ───────────────────────────────────

    @abstractmethod
    def save_issue(self, issue: LegalIssue) -> None: ...
    @abstractmethod
    def get_issue(self, issue_id: UUID) -> LegalIssue | None: ...
    @abstractmethod
    def list_issues(self, case_id: UUID) -> list[LegalIssue]: ...

    # ── Evidence Pack ────────────────────────────

    @abstractmethod
    def build_evidence_pack(self, case_id: UUID) -> EvidencePack: ...

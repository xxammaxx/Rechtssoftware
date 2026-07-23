"""Repository port for legal source provenance operations (M7-A).

Defines the interface that infrastructure must implement for:
- Source registry CRUD
- Snapshot storage and verification
- Instrument/Expression/Provision persistence
- Citation resolution
- FTS5 full-text search
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from private_legal_navigator.domain.legal_source import (
    AuthorityTier,
    ImportStatus,
    InstrumentType,
    LegalCitation,
    LegalExpression,
    LegalInstrument,
    LegalProvision,
    LegalSource,
    ResolutionStatus,
    SourceSnapshot,
)


class LegalSourceRepository(ABC):
    """Port for legal source persistence operations."""

    # ── Sources ──────────────────────────────────

    @abstractmethod
    def initialize_schema(self) -> None: ...
    @abstractmethod
    def save_source(self, source: LegalSource) -> None: ...
    @abstractmethod
    def get_source_by_key(self, source_key: str) -> LegalSource | None: ...
    @abstractmethod
    def get_source(self, source_id: UUID) -> LegalSource | None: ...
    @abstractmethod
    def list_sources(self, *, enabled_only: bool = True) -> list[LegalSource]: ...

    # ── Snapshots ────────────────────────────────

    @abstractmethod
    def save_snapshot(self, snapshot: SourceSnapshot) -> None: ...
    @abstractmethod
    def get_snapshot(self, snapshot_id: UUID) -> SourceSnapshot | None: ...
    @abstractmethod
    def get_snapshot_by_hash(self, sha256: str) -> SourceSnapshot | None: ...
    @abstractmethod
    def update_snapshot_status(
        self, snapshot_id: UUID, status: ImportStatus, error: str = ""
    ) -> None: ...

    # ── Instruments ──────────────────────────────

    @abstractmethod
    def save_instrument(self, instrument: LegalInstrument) -> None: ...
    @abstractmethod
    def get_instrument(self, instrument_id: UUID) -> LegalInstrument | None: ...
    @abstractmethod
    def get_instrument_by_abbreviation(self, abbrev: str) -> LegalInstrument | None: ...
    @abstractmethod
    def list_instruments(
        self,
        *,
        jurisdiction: str = "",
        instrument_type: InstrumentType | None = None,
        authority_tier: AuthorityTier | None = None,
    ) -> list[LegalInstrument]: ...

    # ── Expressions ──────────────────────────────

    @abstractmethod
    def save_expression(self, expression: LegalExpression) -> None: ...
    @abstractmethod
    def get_expression(self, expression_id: UUID) -> LegalExpression | None: ...
    @abstractmethod
    def list_expressions(
        self, instrument_id: UUID, *, current_only: bool = True
    ) -> list[LegalExpression]: ...
    @abstractmethod
    def get_current_expression(self, instrument_id: UUID) -> LegalExpression | None: ...

    # ── Provisions ───────────────────────────────

    @abstractmethod
    def save_provision(self, provision: LegalProvision) -> None: ...
    @abstractmethod
    def get_provision(self, provision_id: UUID) -> LegalProvision | None: ...
    @abstractmethod
    def get_provision_by_stable_key(
        self, expression_id: UUID, stable_key: str
    ) -> LegalProvision | None: ...
    @abstractmethod
    def get_provisions_for_expression(
        self, expression_id: UUID, *, parent_id: UUID | None = None
    ) -> list[LegalProvision]: ...

    # ── Citations ────────────────────────────────

    @abstractmethod
    def save_citation(self, citation: LegalCitation) -> None: ...
    @abstractmethod
    def get_citation(self, citation_id: UUID) -> LegalCitation | None: ...
    @abstractmethod
    def update_citation_resolution(
        self,
        citation_id: UUID,
        status: ResolutionStatus,
        instrument_id: UUID | None = None,
        provision_id: UUID | None = None,
        expression_id: UUID | None = None,
        confidence: str = "UNKNOWN",
        detail: str = "",
    ) -> None: ...

    # ── Search ───────────────────────────────────

    @abstractmethod
    def search_provisions_fts(self, query: str, limit: int = 50) -> list[dict[str, Any]]: ...
    @abstractmethod
    def rebuild_fts_index(self) -> None: ...

"""Domain models for M7-A legal source provenance and corpus.

All entities are immutable where possible. Mutable state (status changes,
versioned corrections) is managed through append-only patterns.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class AuthorityTier(StrEnum):
    """Authority classification for legal sources.

    Tier 0 is the highest authority — official promulgation.
    Tier 3 (CONSOLIDATED_NON_OFFICIAL) is what "Gesetze im Internet" provides.
    """

    OFFICIAL_PROMULGATION = "OFFICIAL_PROMULGATION"
    OFFICIAL_EU_PUBLICATION = "OFFICIAL_EU_PUBLICATION"
    OFFICIAL_COURT_PUBLICATION = "OFFICIAL_COURT_PUBLICATION"
    CONSOLIDATED_NON_OFFICIAL = "CONSOLIDATED_NON_OFFICIAL"
    SECONDARY_SOURCE = "SECONDARY_SOURCE"
    UNKNOWN = "UNKNOWN"


class ImportStatus(StrEnum):
    """Status of a source snapshot import."""

    DOWNLOADED = "DOWNLOADED"
    PARSED = "PARSED"
    NORMALIZED = "NORMALIZED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class InstrumentType(StrEnum):
    """Type of legal instrument."""

    STATUTE = "STATUTE"
    REGULATION = "REGULATION"
    DIRECTIVE = "DIRECTIVE"
    TREATY = "TREATY"
    DECISION = "DECISION"
    ORDER = "ORDER"
    UNKNOWN = "UNKNOWN"


class TemporalStatus(StrEnum):
    """Temporal validity status of a legal expression."""

    CURRENT = "CURRENT"
    AMENDED = "AMENDED"
    REPEALED = "REPEALED"
    NOT_YET_IN_FORCE = "NOT_YET_IN_FORCE"
    UNKNOWN = "UNKNOWN"


class TemporalCompleteness(StrEnum):
    """How complete is the historical record of this expression?"""

    CURRENT_ONLY = "CURRENT_ONLY"
    PARTIAL_HISTORY = "PARTIAL_HISTORY"
    VERIFIED_HISTORY = "VERIFIED_HISTORY"
    UNKNOWN = "UNKNOWN"


class TemporalConfidence(StrEnum):
    """Confidence level for temporal range data."""

    CONFIRMED = "CONFIRMED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class ProvisionType(StrEnum):
    """Structural type of a legal provision."""

    PARAGRAPH = "PARAGRAPH"
    ARTICLE = "ARTICLE"
    SECTION = "SECTION"
    CLAUSE = "CLAUSE"
    SENTENCE = "SENTENCE"
    NUMBER = "NUMBER"
    LETTER = "LETTER"
    HEADING = "HEADING"
    OTHER = "OTHER"


class ResolutionStatus(StrEnum):
    """Status of a citation resolution attempt."""

    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    PENDING = "PENDING"


class ResolutionConfidence(StrEnum):
    """Confidence in a citation resolution."""

    EXACT = "EXACT"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


# ──────────────────────────────────────────────
# Domain Entities
# ──────────────────────────────────────────────


@dataclass
class LegalSource:
    """A registered legal source (publisher/distributor of legal materials).

    Each source has a fixed authority tier and jurisdiction.
    Sources are defined at setup time, not dynamically created.
    """

    source_id: UUID | None
    source_key: str
    display_name: str
    authority_tier: AuthorityTier
    jurisdiction: str
    enabled: bool = True
    created_at: datetime | None = None
    base_url: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if self.source_id is None:
            self.source_id = uuid4()
        if not self.source_key:
            raise ValueError("source_key must not be empty")
        if not self.display_name:
            raise ValueError("display_name must not be empty")


@dataclass
class SourceSnapshot:
    """An immutable raw download from a legal source.

    Stored unmodified. SHA-256 hash computed at download time.
    The raw snapshot must never be altered — normalization creates
    separate derived data.
    """

    snapshot_id: UUID | None
    source_id: UUID
    source_locator: str
    retrieved_at: datetime
    content_type: str
    byte_size: int
    sha256: str
    storage_path: str
    parser_version: str = ""
    import_status: ImportStatus = ImportStatus.DOWNLOADED
    error_summary: str = ""
    immutable: bool = True
    http_etag: str = ""
    http_last_modified: str = ""

    def __post_init__(self) -> None:
        if self.snapshot_id is None:
            self.snapshot_id = uuid4()
        if not self.sha256 or len(self.sha256) != 64:
            raise ValueError("sha256 must be a 64-character hex string")
        if self.byte_size < 0:
            raise ValueError("byte_size must be >= 0")
        if not self.source_locator:
            raise ValueError("source_locator must not be empty")


@dataclass
class LegalInstrument:
    """A legal instrument (law, regulation, directive, etc.)."""

    instrument_id: UUID | None
    jurisdiction: str
    instrument_type: InstrumentType
    official_title: str
    short_title: str = ""
    abbreviation: str = ""
    source_identifier: str = ""
    authority_tier: AuthorityTier = AuthorityTier.UNKNOWN
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is None:
            self.instrument_id = uuid4()
        if not self.official_title:
            raise ValueError("official_title must not be empty")


@dataclass
class LegalExpression:
    """A specific version/edition/time-slice of a LegalInstrument."""

    expression_id: UUID | None
    instrument_id: UUID
    source_snapshot_id: UUID
    published_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    retrieved_at: datetime | None = None
    temporal_status: TemporalStatus = TemporalStatus.UNKNOWN
    historical_completeness: TemporalCompleteness = TemporalCompleteness.CURRENT_ONLY
    temporal_confidence: TemporalConfidence = TemporalConfidence.UNKNOWN
    source_note: str = ""

    def __post_init__(self) -> None:
        if self.expression_id is None:
            self.expression_id = uuid4()


@dataclass
class LegalProvision:
    """A paragraph, article, section, or other structural unit of law.

    Example: § 48 SGB X (Aufhebung eines Verwaltungsaktes)
    """

    provision_id: UUID | None
    expression_id: UUID
    provision_type: ProvisionType
    provision_number: str
    heading: str = ""
    stable_key: str = ""
    parent_provision_id: UUID | None = None
    sort_key: str = ""
    text_content: str = ""
    text_sha256: str = ""

    def __post_init__(self) -> None:
        if self.provision_id is None:
            self.provision_id = uuid4()
        if not self.provision_number:
            raise ValueError("provision_number must not be empty")


@dataclass
class LegalCitation:
    """A citation resolution record — mapping a citation string to a provision.

    Stores both the original citation text and the resolution result.
    """

    citation_id: UUID | None
    source_entity_type: str = ""  # "case", "document", "evidence"
    source_entity_id: UUID | None = None
    citation_text: str = ""
    resolved_instrument_id: UUID | None = None
    resolved_provision_id: UUID | None = None
    resolution_status: ResolutionStatus = ResolutionStatus.PENDING
    resolution_confidence: ResolutionConfidence = ResolutionConfidence.UNKNOWN
    reviewed_at: datetime | None = None
    resolved_expression_id: UUID | None = None
    resolution_detail: str = ""

    def __post_init__(self) -> None:
        if self.citation_id is None:
            self.citation_id = uuid4()


# ──────────────────────────────────────────────
# Value Objects
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class CitationRequest:
    """A request to resolve a legal citation to a specific provision."""

    raw: str
    law_abbreviation: str = ""
    paragraph: str = ""
    paragraph_number: str = ""
    clause_number: str = ""
    sentence_number: str = ""
    alternative_number: str = ""
    target_date: datetime | None = None

    def __post_init__(self) -> None:
        if not self.raw.strip():
            raise ValueError("Citation raw text must not be empty")

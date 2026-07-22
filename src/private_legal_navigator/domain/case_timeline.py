"""Domain models for M7-A case legal timeline and legal links.

All event and link state changes are append-only:
- Corrections create new records, old ones are preserved.
- Revocations set revoked_at but preserve the record.
- This matches the ADR-002 RefEvent pattern (supersedes/revoke).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class LegalEventType(StrEnum):
    """Semantic categories of legal events in a case.

    These are descriptive labels. They do NOT trigger any automatic
    legal effects. Every event requires human review.
    """

    DOCUMENT_ISSUED = "DOCUMENT_ISSUED"
    DOCUMENT_RECEIVED = "DOCUMENT_RECEIVED"
    DOCUMENT_OPENED = "DOCUMENT_OPENED"
    ADMINISTRATIVE_ACT_EFFECTIVE = "ADMINISTRATIVE_ACT_EFFECTIVE"
    HEARING_STARTED = "HEARING_STARTED"
    OBJECTION_FILED = "OBJECTION_FILED"
    DECISION_AMENDED = "DECISION_AMENDED"
    DECISION_REVOKED = "DECISION_REVOKED"
    PAYMENT_REQUESTED = "PAYMENT_REQUESTED"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    DEADLINE_STARTED = "DEADLINE_STARTED"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    LEGAL_ACTION_FILED = "LEGAL_ACTION_FILED"
    OTHER = "OTHER"


class LegalEventRelationType(StrEnum):
    """Relationship types between legal events.

    These are explicitly assigned by the user. No automatic inference.
    """

    AMENDS = "AMENDS"
    REPLACES = "REPLACES"
    REVOKES = "REVOKES"
    CHALLENGES = "CHALLENGES"
    RESPONDS_TO = "RESPONDS_TO"
    EVIDENCES = "EVIDENCES"
    CONTRADICTS = "CONTRADICTS"
    TRIGGERS_DEADLINE = "TRIGGERS_DEADLINE"
    PARTIALLY_RESOLVES = "PARTIALLY_RESOLVES"
    OTHER = "OTHER"


class ReviewStatus(StrEnum):
    """Human review lifecycle for legal events and links.

    All items start as CANDIDATE and require explicit human confirmation.
    Matches the pattern from ADR-002 (ConfirmationStatus).
    """

    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class LegalLinkStatus(StrEnum):
    """Status of a case-legal-provision link.

    All links start as CANDIDATE. The user must explicitly confirm.
    """

    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"
    REVOKED = "REVOKED"


class EvidenceType(StrEnum):
    """Type of evidence supporting or contradicting a legal claim."""

    PROVISION = "PROVISION"
    COURT_DECISION = "COURT_DECISION"
    CASE_DOCUMENT = "CASE_DOCUMENT"
    CASE_EVENT = "CASE_EVENT"
    SECONDARY_SOURCE = "SECONDARY_SOURCE"
    USER_NOTE = "USER_NOTE"
    OTHER = "OTHER"


class Stance(StrEnum):
    """How a piece of evidence relates to a claim."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class LegalIssueStatus(StrEnum):
    """Status of a legal issue in a case."""

    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"


class ClaimType(StrEnum):
    """Type of legal claim/hypothesis."""

    RIGHT = "RIGHT"
    OBLIGATION = "OBLIGATION"
    PROCEDURAL = "PROCEDURAL"
    FACTUAL = "FACTUAL"
    INTERPRETIVE = "INTERPRETIVE"


class ClaimStatus(StrEnum):
    """Status of a legal claim."""

    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class OperatingMode(StrEnum):
    """Legal operating mode — compliance gate for RDG § 2/§ 3 boundaries.

    OWNER_SELF_HELP: user's own legal matters.
    PROFESSIONAL_ASSISTED: used by a legal professional for their client.
    THIRD_PARTY_SERVICE: blocked until legal review completed.
    """

    OWNER_SELF_HELP = "OWNER_SELF_HELP"
    PROFESSIONAL_ASSISTED = "PROFESSIONAL_ASSISTED"
    THIRD_PARTY_SERVICE = "THIRD_PARTY_SERVICE"


# ──────────────────────────────────────────────
# Domain Entities
# ──────────────────────────────────────────────


@dataclass
class CaseLegalEvent:
    """A legal event in a specific case.

    Append-only. Corrections create new records with previous_event_id.
    Revocations set revoked_at. All three time dimensions are tracked.
    """

    event_id: UUID
    case_id: UUID
    event_type: LegalEventType
    occurred_at: datetime | None = None
    known_at: datetime | None = None
    recorded_at: datetime | None = None
    title: str = ""
    description: str = ""
    source_document_id: UUID | None = None
    review_status: ReviewStatus = ReviewStatus.CANDIDATE
    confidence: str = "LOW"
    previous_event_id: UUID | None = None
    revoked_at: datetime | None = None
    actor: str = ""
    amount: str = ""
    legal_effect_note: str = ""

    def __post_init__(self) -> None:
        if self.event_id is None:
            self.event_id = uuid4()
        if self.recorded_at is None:
            self.recorded_at = datetime.now()
        if self.title and len(self.title) > 500:
            raise ValueError("title must not exceed 500 characters")
        if self.description and len(self.description) > 5000:
            raise ValueError("description must not exceed 5000 characters")
        if self.legal_effect_note and len(self.legal_effect_note) > 2000:
            raise ValueError("legal_effect_note must not exceed 2000 characters")


@dataclass
class EventRelation:
    """A directed relationship between two legal events.

    Many-to-many. Both events must belong to the same case.
    """

    relation_id: UUID
    case_id: UUID
    source_event_id: UUID
    target_event_id: UUID
    relation_type: LegalEventRelationType
    note: str = ""
    review_status: ReviewStatus = ReviewStatus.CANDIDATE
    created_at: datetime | None = None
    confirmed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.relation_id is None:
            self.relation_id = uuid4()
        if self.source_event_id == self.target_event_id:
            raise ValueError("Event relation cannot be self-referential")


@dataclass
class CaseLegalLink:
    """A link between a case (or document) and a legal provision.

    All links start as CANDIDATE. The user must explicitly confirm.
    Corrected/revoked records are preserved via previous_link_id.
    """

    link_id: UUID
    case_id: UUID
    legal_provision_id: UUID
    document_id: UUID | None = None
    relevance_note: str = ""
    status: LegalLinkStatus = LegalLinkStatus.CANDIDATE
    created_at: datetime | None = None
    confirmed_at: datetime | None = None
    revoked_at: datetime | None = None
    previous_link_id: UUID | None = None
    confirmed_by: str = ""

    def __post_init__(self) -> None:
        if self.link_id is None:
            self.link_id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.relevance_note and len(self.relevance_note) > 2000:
            raise ValueError("relevance_note must not exceed 2000 characters")
        if self.confirmed_by and len(self.confirmed_by) > 100:
            raise ValueError("confirmed_by must not exceed 100 characters")


@dataclass
class LegalIssue:
    """A legal question/issue identified in a case.

    Initially detected by deterministic spotter, later confirmed by human.
    """

    issue_id: UUID
    case_id: UUID
    title: str
    description: str = ""
    status: LegalIssueStatus = LegalIssueStatus.OPEN
    source: str = "MANUAL"
    confidence: str = "LOW"
    created_at: datetime | None = None
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.issue_id is None:
            self.issue_id = uuid4()
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if len(self.title) > 500:
            raise ValueError("title must not exceed 500 characters")


@dataclass
class LegalClaim:
    """A legal hypothesis/claim about a case.

    Supports and contradictions are tracked via claim_evidence.
    No LLM needed for M7-A — deterministic or manual population.
    """

    claim_id: UUID
    case_id: UUID
    legal_issue_id: UUID | None = None
    claim_text: str = ""
    claim_type: ClaimType = ClaimType.INTERPRETIVE
    status: ClaimStatus = ClaimStatus.DRAFT
    created_by: str = "USER"
    created_at: datetime | None = None
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.claim_id is None:
            self.claim_id = uuid4()
        if self.claim_text and len(self.claim_text) > 5000:
            raise ValueError("claim_text must not exceed 5000 characters")


@dataclass
class ClaimEvidence:
    """A piece of evidence supporting or contradicting a legal claim."""

    evidence_id: UUID
    claim_id: UUID
    evidence_type: EvidenceType
    legal_provision_id: UUID | None = None
    case_document_id: UUID | None = None
    case_event_id: UUID | None = None
    quoted_span: str = ""
    stance: Stance = Stance.NEUTRAL
    source_hash: str = ""
    note: str = ""
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.evidence_id is None:
            self.evidence_id = uuid4()
        if self.quoted_span and len(self.quoted_span) > 10000:
            raise ValueError("quoted_span must not exceed 10000 characters")


# ──────────────────────────────────────────────
# Evidence Pack (Value Object)
# ──────────────────────────────────────────────


@dataclass
class EvidencePack:
    """A structured, deterministic bundle of evidence for a case.

    Contains only confirmed items. Candidates are excluded.
    Revoked items are excluded. Quellenhashes are included.
    No LLM is used to populate this — it's a pure projection.
    """

    schema_version: str = "1.0.0"
    case_id: UUID | None = None
    case_title: str = ""
    exported_at: datetime | None = None
    operating_mode: OperatingMode = OperatingMode.OWNER_SELF_HELP
    confirmed_facts: list[dict] = field(default_factory=list)
    open_facts: list[dict] = field(default_factory=list)
    legal_events: list[dict] = field(default_factory=list)
    legal_issues: list[dict] = field(default_factory=list)
    confirmed_legal_links: list[dict] = field(default_factory=list)
    provisions: list[dict] = field(default_factory=list)
    source_snapshots: list[dict] = field(default_factory=list)
    temporal_warnings: list[str] = field(default_factory=list)
    integrity: dict = field(default_factory=dict)

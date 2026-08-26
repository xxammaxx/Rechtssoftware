"""Data models for BescheidPilot local document analysis.

All models are plain dataclasses with no I/O, network, or external
dependencies. Designed for deterministic local extraction and
source-evidence tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    """A single piece of evidence anchored to a source text position.

    Every critical extraction MUST have at least one EvidenceSpan.
    If no source quote exists, the finding is marked as uncertain.
    """

    field: str
    """Which analytical field this evidence supports (e.g. 'deadline')."""

    value: str
    """The extracted value."""

    quote: str
    """Short verbatim quote from the source text."""

    start: int
    """Character offset where the quote begins."""

    end: int
    """Character offset where the quote ends."""

    confidence: float = 1.0
    """0.0 (guessing) to 1.0 (highly confident)."""


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """A single field flagged for mandatory human review.

    No field may be treated as final or legally binding without
    explicit human confirmation. ReviewItems are generated
    automatically but never set to ``reviewed`` automatically.
    """

    field: str
    """Which analytical field this review covers."""

    value: str | None
    """The extracted value that needs review (None if missing)."""

    status: str = "requires_review"
    """One of 'requires_review', 'reviewed', 'unknown', 'not_applicable'."""

    reason: str = ""
    """Why this field requires review."""

    evidence_required: bool = True
    """Whether evidence must exist for this field."""

    evidence_present: bool = False
    """Whether at least one EvidenceSpan exists for this field."""

    severity: str = "MEDIUM"
    """One of 'HIGH', 'MEDIUM', 'LOW'."""


@dataclass(frozen=True, slots=True)
class AnswerDraft:
    """A review-required local answer draft.

    Never treated as final, never transmitted automatically. Always
    requires explicit human review and approval before any use.
    """

    title: str
    """Draft title, e.g. 'Rückmeldung zu Aufforderung zur Mitwirkung'."""

    body: str
    """The full draft text."""

    status: str = "draft_requires_review"
    """Always 'draft_requires_review' — never auto-approved."""

    requires_review: bool = True
    """Always True."""

    based_on_fields: list[str] = field(default_factory=list)
    """List of field names this draft used from the analysis."""

    warnings: list[str] = field(default_factory=list)
    """Warnings about missing or uncertain data used in the draft."""

    final_decision: bool = False
    """Always False."""


@dataclass(frozen=True, slots=True)
class BescheidAnalysisResult:
    """Structured facts extracted from a single Bescheid document.

    Every field that contains a non-None value should have at least one
    corresponding EvidenceSpan in ``evidence``. Fields that cannot be
    reliably determined are ``None`` (for scalars) or empty (for lists).
    """

    authority: str | None = None
    """Recognised issuing authority, e.g. 'Jobcenter Musterstadt'."""

    document_type: str | None = None
    """Document type, e.g. 'Aufforderung zur Mitwirkung'."""

    letter_date: str | None = None
    """Date of the letter, if clearly stated."""

    deadline: str | None = None
    """Deadline text, e.g. 'bis zum 15.07.2026'. Never computed from
    relative expressions without clear anchor base."""

    required_action: str | None = None
    """What the recipient must do, e.g. 'Unterlagen einreichen'."""

    missing_documents: list[str] = field(default_factory=list)
    """Documents the authority asks the recipient to submit."""

    risk_level: str = "unknown"
    """One of 'low', 'medium', 'high', 'unknown'."""

    evidence: list[EvidenceSpan] = field(default_factory=list)
    """Source-anchored evidence for every critical extraction."""

    warnings: list[str] = field(default_factory=list)
    """Non-blocking warnings about uncertain or missing data."""

    review_required: bool = False
    """True when at least one critical field needs human review."""

    review_items: list[ReviewItem] = field(default_factory=list)
    """Items flagged for mandatory human review."""

    final_decision: bool = False
    """Always False — no analysis result is legally final."""

    answer_draft: AnswerDraft | None = None
    """Optional review-required answer draft. Never auto-generated without
    explicit request. Always requires human review."""

    @property
    def has_any_content(self) -> bool:
        """Return True when at least one field was populated."""
        return (
            self.authority is not None
            or self.document_type is not None
            or self.letter_date is not None
            or self.deadline is not None
            or self.required_action is not None
            or len(self.missing_documents) > 0
        )

    @property
    def has_deadline(self) -> bool:
        return self.deadline is not None

    @property
    def has_required_action(self) -> bool:
        return self.required_action is not None

    @property
    def critical_warnings(self) -> list[str]:
        """Warnings about missing critical information."""
        critical: list[str] = []
        if self.deadline is None:
            critical.append("Keine Frist erkannt — manuelle Prüfung erforderlich")
        if self.required_action is None:
            critical.append("Keine Handlungspflicht erkannt — manuelle Prüfung erforderlich")
        return critical

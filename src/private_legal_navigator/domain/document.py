"""Domain model for a Document attached to a Case."""

import uuid
from datetime import UTC, datetime


class Document:
    """A document uploaded to a case.

    Invariants:
        - document_id is a server-generated UUIDv4
        - filename is the original filename (max 255 chars)
        - mime_type must be application/pdf (M2 only)
        - size_bytes must be > 0 and ≤ 20 MB
        - case_id references the parent case
        - created_at is timezone-aware UTC
        - doc_type is one of: bescheid, rechnung, mahnung, vertrag, widerspruch, sonstiges
        - classification_confidence is 0.0–1.0 (ratio-model: matched/total patterns)
        - matched_patterns is a list of matched regex pattern strings (JSON TEXT in DB)
    """

    ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"application/pdf"})
    MAX_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB

    def __init__(
        self,
        filename: str,
        mime_type: str,
        size_bytes: int,
        case_id: uuid.UUID,
        *,
        document_id: uuid.UUID | None = None,
        storage_path: str | None = None,
        created_at: datetime | None = None,
        text_content: str = "",
        doc_type: str = "sonstiges",
        classification_confidence: float = 0.0,
        matched_patterns: list[str] | None = None,
    ) -> None:
        self._validate_mime_type(mime_type)
        self._validate_size(size_bytes)

        self.document_id = document_id or uuid.uuid4()
        self.case_id = case_id
        self.filename = filename
        self.mime_type = mime_type
        self.size_bytes = size_bytes
        self.storage_path = storage_path or f"{self.document_id}.bin"
        self.created_at = created_at or datetime.now(UTC)
        self.text_content = text_content
        self.doc_type = doc_type
        self.classification_confidence = classification_confidence
        self.matched_patterns = matched_patterns or []

    @classmethod
    def _validate_mime_type(cls, mime_type: str) -> None:
        if mime_type not in cls.ALLOWED_MIME_TYPES:
            raise ValueError("Nur PDF-Dateien sind erlaubt.")

    @classmethod
    def _validate_size(cls, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise ValueError("Dateigröße muss positiv sein.")
        if size_bytes > cls.MAX_SIZE_BYTES:
            raise ValueError(
                f"Die Datei überschreitet die maximale Größe von "
                f"{cls.MAX_SIZE_BYTES // (1024 * 1024)} MB."
            )

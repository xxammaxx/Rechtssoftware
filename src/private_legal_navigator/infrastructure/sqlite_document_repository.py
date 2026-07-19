"""SQLite implementation of DocumentRepository."""

import contextlib
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.domain.document import Document
from private_legal_navigator.infrastructure.database import get_connection

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    text_content TEXT NOT NULL DEFAULT '',
    extraction_error TEXT DEFAULT NULL,
    doc_type TEXT NOT NULL DEFAULT 'sonstiges',
    classification_confidence REAL NOT NULL DEFAULT 0.0,
    matched_patterns TEXT NOT NULL DEFAULT '[]'
)
"""

ALTER_ADD_EXTRACTION_ERROR = "ALTER TABLE documents ADD COLUMN extraction_error TEXT DEFAULT NULL"

CREATE_DOCUMENTS_INDEX = "CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id)"


class SqliteDocumentRepository(DocumentRepository):
    """SQLite-backed implementation of DocumentRepository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Idempotent schema initialization for documents table."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(CREATE_DOCUMENTS_TABLE)
            conn.execute(CREATE_DOCUMENTS_INDEX)
            # Idempotent migration: add extraction_error if not present
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(ALTER_ADD_EXTRACTION_ERROR)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  DocumentRepository interface
    # ------------------------------------------------------------------ #

    def save(self, document: Document) -> None:
        """Insert document metadata."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO documents
                    (document_id, case_id, filename,
                     mime_type, size_bytes, storage_path, created_at,
                     text_content, extraction_error, doc_type, classification_confidence,
                     matched_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(document.document_id),
                    str(document.case_id),
                    document.filename,
                    document.mime_type,
                    document.size_bytes,
                    document.storage_path,
                    document.created_at.isoformat(),
                    document.text_content,
                    document.extraction_error,
                    document.doc_type,
                    document.classification_confidence,
                    json.dumps(document.matched_patterns),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Retrieve document metadata by ID."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT document_id, case_id, filename, mime_type, "
                "size_bytes, storage_path, created_at, text_content, "
                "extraction_error, doc_type, classification_confidence, matched_patterns "
                "FROM documents WHERE document_id = ?",
                (str(document_id),),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        return self._row_to_doc(row)

    def list_by_case(self, case_id: uuid.UUID) -> list[Document]:
        """List all documents for a given case."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT document_id, case_id, filename, mime_type, "
                "size_bytes, storage_path, created_at, text_content, "
                "extraction_error, doc_type, classification_confidence, matched_patterns "
                "FROM documents WHERE case_id = ? "
                "ORDER BY created_at DESC",
                (str(case_id),),
            ).fetchall()
        finally:
            conn.close()

        return [self._row_to_doc(row) for row in rows]

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_doc(row: sqlite3.Row) -> Document:
        """Convert a database row to a Document entity."""
        return Document(
            filename=row["filename"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            case_id=uuid.UUID(row["case_id"]),
            document_id=uuid.UUID(row["document_id"]),
            storage_path=row["storage_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            text_content=row["text_content"],
            extraction_error=row["extraction_error"],
            doc_type=row["doc_type"],
            classification_confidence=row["classification_confidence"],
            matched_patterns=json.loads(row["matched_patterns"]),
        )

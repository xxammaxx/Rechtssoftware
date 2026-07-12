"""Integration tests for LocalFileStorage and SqliteDocumentRepository."""

import uuid
from pathlib import Path

import pytest

from private_legal_navigator.domain.document import Document
from private_legal_navigator.infrastructure.local_file_storage import LocalFileStorage
from private_legal_navigator.infrastructure.sqlite_document_repository import (
    SqliteDocumentRepository,
)


class TestLocalFileStorage:
    """Tests for the local file storage implementation."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> LocalFileStorage:
        return LocalFileStorage(tmp_path / "documents")

    def test_store_and_retrieve(self, storage: LocalFileStorage) -> None:
        """Store and retrieve file content."""
        content = b"%PDF-1.4 fake pdf content"
        storage.store("test.bin", content)
        assert storage.exists("test.bin")
        assert storage.retrieve("test.bin") == content

    def test_retrieve_nonexistent_raises(self, storage: LocalFileStorage) -> None:
        """Retrieving a nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            storage.retrieve("nonexistent.bin")

    def test_exists_returns_false(self, storage: LocalFileStorage) -> None:
        """exists should return False for nonexistent files."""
        assert not storage.exists("nonexistent.bin")

    def test_path_traversal_prevented(self, storage: LocalFileStorage) -> None:
        """Path traversal in storage_path should be neutralized."""
        content = b"safe"
        storage.store("../../etc/passwd", content)
        # The traversal was neutralized: only the filename "passwd" was used
        # The full traversal path should not create subdirectories
        target = storage._base_dir / "passwd"
        assert target.exists()
        # The traversal path should NOT exist as a subdirectory
        assert not (storage._base_dir / ".." / ".." / "etc" / "passwd").exists()


class TestSqliteDocumentRepository:
    """Tests for SQLite document metadata repository."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> Path:
        return tmp_path / "test.db"

    @pytest.fixture
    def repo(self, db_path: Path) -> SqliteDocumentRepository:
        r = SqliteDocumentRepository(db_path)
        r.initialize_schema()
        return r

    def _make_doc(self, case_id: uuid.UUID, filename: str = "test.pdf") -> Document:
        return Document(
            filename=filename,
            mime_type="application/pdf",
            size_bytes=1024,
            case_id=case_id,
        )

    def test_save_and_get_by_id(self, repo: SqliteDocumentRepository) -> None:
        """Save and retrieve document metadata."""
        case_id = uuid.uuid4()
        doc = self._make_doc(case_id)
        repo.save(doc)

        retrieved = repo.get_by_id(doc.document_id)
        assert retrieved is not None
        assert retrieved.document_id == doc.document_id
        assert retrieved.filename == "test.pdf"
        assert retrieved.case_id == case_id

    def test_list_by_case(self, repo: SqliteDocumentRepository) -> None:
        """List documents for a specific case."""
        case_id = uuid.uuid4()
        doc1 = self._make_doc(case_id, "a.pdf")
        doc2 = self._make_doc(case_id, "b.pdf")
        repo.save(doc1)
        repo.save(doc2)

        docs = repo.list_by_case(case_id)
        assert len(docs) == 2

    def test_list_by_case_empty(self, repo: SqliteDocumentRepository) -> None:
        """List documents for a case with no documents."""
        docs = repo.list_by_case(uuid.uuid4())
        assert docs == []

    def test_get_by_id_returns_none(self, repo: SqliteDocumentRepository) -> None:
        """Unknown document ID returns None."""
        assert repo.get_by_id(uuid.uuid4()) is None

    def test_schema_is_idempotent(self, repo: SqliteDocumentRepository) -> None:
        """Calling initialize_schema twice should not raise."""
        repo.initialize_schema()

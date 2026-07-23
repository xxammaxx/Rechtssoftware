"""Start FastAPI test server with temp database and seed data.

Usage: python tests/e2e/server.py <data_dir> <port>
"""

import json
import sys
import uuid
from datetime import date, datetime, UTC
from pathlib import Path

import uvicorn

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings


def seed_test_data(data_dir: Path) -> dict:
    """Create synthetic test data for E2E tests."""
    from private_legal_navigator.application.case_service import CaseService
    from private_legal_navigator.application.document_service import DocumentService
    from private_legal_navigator.domain.case import Case
    from private_legal_navigator.domain.document import Document
    from private_legal_navigator.infrastructure.sqlite_case_repository import (
        SqliteCaseRepository,
    )
    from private_legal_navigator.infrastructure.sqlite_document_repository import (
        SqliteDocumentRepository,
    )
    from private_legal_navigator.infrastructure.local_file_storage import (
        LocalFileStorage,
    )

    case_repo = SqliteCaseRepository(data_dir / "pln.db")
    doc_repo = SqliteDocumentRepository(data_dir / "pln.db")
    file_storage = LocalFileStorage(data_dir / "documents")

    from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor
    from private_legal_navigator.infrastructure.rule_based_classifier import RuleBasedClassifier

    text_extractor = PdfTextExtractor()
    classifier = RuleBasedClassifier()

    case_service = CaseService(case_repo)
    doc_service = DocumentService(doc_repo, file_storage, case_repo, text_extractor, classifier)

    # Create test case
    test_case = case_service.create_case("SYNTHETISCH – E2E Testfall Slice 3")
    case_id = str(test_case.case_id)

    # Create test document with synthetic text containing deadline candidates
    test_text = (
        "Bescheid vom 15.06.2026\n\n"
        "Sehr geehrte Damen und Herren,\n\n"
        "hiermit ergeht folgender Bescheid. Sie können innerhalb von 14 Tagen "
        "Widerspruch einlegen. Die Frist beginnt mit der Bekanntgabe.\n\n"
        "Mit freundlichen Grüßen\n"
        "Die Behörde\n"
    )
    test_pdf = b"%PDF-1.4\n%" + test_text.encode("utf-8")

    doc = doc_service.upload_document(
        case_id=test_case.case_id,
        filename="SYNTHETISCH – Testbescheid.pdf",
        content=test_pdf,
        mime_type="application/pdf",
        size_bytes=len(test_pdf),
    )
    document_id = str(doc.document_id)

    seed = {
        "case_id": case_id,
        "document_id": document_id,
        "case_title": test_case.title,
        "document_filename": doc.filename,
        "created_at": datetime.now(UTC).isoformat(),
    }

    seed_file = data_dir / "seed_data.json"
    seed_file.write_text(json.dumps(seed, indent=2))

    return seed


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python server.py <data_dir> <port>")
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    port = int(sys.argv[2])

    # Initialize database schema BEFORE seeding
    from private_legal_navigator.infrastructure.sqlite_case_repository import SqliteCaseRepository
    from private_legal_navigator.infrastructure.sqlite_document_repository import (
        SqliteDocumentRepository,
    )
    from private_legal_navigator.infrastructure.sqlite_reference_event_repository import (
        SqliteReferenceEventRepository,
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "documents").mkdir(exist_ok=True)

    db_path = data_dir / "pln.db"
    SqliteCaseRepository(db_path).initialize_schema()
    SqliteDocumentRepository(db_path).initialize_schema()
    SqliteReferenceEventRepository(db_path).initialize_schema()

    # Seed test data
    seed_test_data(data_dir)

    settings = Settings(data_dir=data_dir, host="127.0.0.1", port=port)
    app = create_app(settings)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

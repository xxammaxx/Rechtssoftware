"""SQLite implementation of the CaseRepository port."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.domain.case import Case, CaseStatus
from private_legal_navigator.infrastructure.database import get_connection, initialize_schema


class SqliteCaseRepository(CaseRepository):
    """SQLite-backed implementation of CaseRepository.

    Uses parametrized queries exclusively. Each method opens and closes
    its own connection to avoid threading issues.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Idempotent schema initialization."""
        initialize_schema(self._db_path)

    # ------------------------------------------------------------------ #
    #  CaseRepository interface
    # ------------------------------------------------------------------ #

    def save(self, case: Case) -> None:
        """Insert or replace a case."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO cases (case_id, title, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(case.case_id),
                    case.title,
                    case.status.value,
                    case.created_at.isoformat(),
                    case.updated_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, case_id: uuid.UUID) -> Case | None:
        """Retrieve a case by its UUID. Returns None if not found."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT case_id, title, status, created_at, updated_at "
                "FROM cases WHERE case_id = ?",
                (str(case_id),),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return self._row_to_case(row)

    def list_all(self) -> list[Case]:
        """Return all cases sorted by created_at descending."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT case_id, title, status, created_at, updated_at "
                "FROM cases ORDER BY created_at DESC"
            ).fetchall()
        finally:
            conn.close()

        return [self._row_to_case(row) for row in rows]

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_case(row: sqlite3.Row) -> Case:
        """Convert a database row into a Case domain entity."""
        return Case(
            case_id=uuid.UUID(row["case_id"]),
            title=row["title"],
            status=CaseStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

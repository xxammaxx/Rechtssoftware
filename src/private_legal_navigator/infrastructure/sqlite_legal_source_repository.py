"""SQLite implementation of LegalSourceRepository (M7-A)."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from private_legal_navigator.application.legal_source_repository import LegalSourceRepository
from private_legal_navigator.domain.legal_source import (
    AuthorityTier,
    ImportStatus,
    InstrumentType,
    LegalCitation,
    LegalExpression,
    LegalInstrument,
    LegalProvision,
    LegalSource,
    ResolutionConfidence,
    ResolutionStatus,
    SourceSnapshot,
    TemporalCompleteness,
    TemporalConfidence,
    TemporalStatus,
)
from private_legal_navigator.domain.sync import SyncItem, SyncItemStatus, SyncRun, SyncRunStatus
from private_legal_navigator.infrastructure.database import get_connection, initialize_schema


class SqliteLegalSourceRepository(LegalSourceRepository):
    """SQLite-backed implementation of LegalSourceRepository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        initialize_schema(self._db_path)

    # ── Sources ──────────────────────────────────

    def save_source(self, source: LegalSource) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_sources
                    (source_id, source_key, display_name, authority_tier,
                     jurisdiction, enabled, created_at, base_url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(source.source_id),
                    source.source_key,
                    source.display_name,
                    source.authority_tier.value,
                    source.jurisdiction,
                    1 if source.enabled else 0,
                    (source.created_at or datetime.now()).isoformat(),
                    source.base_url,
                    source.description,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_source_by_key(self, source_key: str) -> LegalSource | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_sources WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_source(row)
        finally:
            conn.close()

    def get_source(self, source_id: uuid.UUID) -> LegalSource | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_sources WHERE source_id = ?",
                (str(source_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_source(row)
        finally:
            conn.close()

    def list_sources(self, *, enabled_only: bool = True) -> list[LegalSource]:
        conn = get_connection(self._db_path)
        try:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM legal_sources WHERE enabled = 1 ORDER BY display_name"
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM legal_sources ORDER BY display_name").fetchall()
            return [self._row_to_source(row) for row in rows]
        finally:
            conn.close()

    # ── Snapshots ────────────────────────────────

    def save_snapshot(
        self, snapshot: SourceSnapshot, conn: sqlite3.Connection | None = None
    ) -> None:
        if conn is not None:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_source_snapshots
                    (snapshot_id, source_id, source_locator, retrieved_at,
                     content_type, byte_size, sha256, storage_path,
                     parser_version, import_status, error_summary, immutable,
                     http_etag, http_last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(snapshot.snapshot_id),
                    str(snapshot.source_id),
                    snapshot.source_locator,
                    snapshot.retrieved_at.isoformat(),
                    snapshot.content_type,
                    snapshot.byte_size,
                    snapshot.sha256,
                    snapshot.storage_path,
                    snapshot.parser_version,
                    snapshot.import_status.value,
                    snapshot.error_summary,
                    1 if snapshot.immutable else 0,
                    snapshot.http_etag,
                    snapshot.http_last_modified,
                ),
            )
            return
        # Standalone: create own connection and commit
        _conn = get_connection(self._db_path)
        try:
            _conn.execute(
                """
                INSERT OR REPLACE INTO legal_source_snapshots
                    (snapshot_id, source_id, source_locator, retrieved_at,
                     content_type, byte_size, sha256, storage_path,
                     parser_version, import_status, error_summary, immutable,
                     http_etag, http_last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(snapshot.snapshot_id),
                    str(snapshot.source_id),
                    snapshot.source_locator,
                    snapshot.retrieved_at.isoformat(),
                    snapshot.content_type,
                    snapshot.byte_size,
                    snapshot.sha256,
                    snapshot.storage_path,
                    snapshot.parser_version,
                    snapshot.import_status.value,
                    snapshot.error_summary,
                    1 if snapshot.immutable else 0,
                    snapshot.http_etag,
                    snapshot.http_last_modified,
                ),
            )
            _conn.commit()
        finally:
            _conn.close()

    def get_snapshot(self, snapshot_id: uuid.UUID) -> SourceSnapshot | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_source_snapshots WHERE snapshot_id = ?",
                (str(snapshot_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_snapshot(row)
        finally:
            conn.close()

    def get_snapshot_by_hash(self, sha256: str) -> SourceSnapshot | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_source_snapshots "
                "WHERE sha256 = ? ORDER BY retrieved_at DESC LIMIT 1",
                (sha256,),
            ).fetchone()
            return self._row_to_snapshot(row) if row else None
        finally:
            conn.close()

    def update_snapshot_status(
        self, snapshot_id: uuid.UUID, status: ImportStatus, error: str = ""
    ) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "UPDATE legal_source_snapshots SET import_status = ?, error_summary = ? "
                "WHERE snapshot_id = ?",
                (status.value, error, str(snapshot_id)),
            )
            conn.commit()
        finally:
            conn.close()

    def list_snapshots_for_source(self, source_key: str) -> list[SourceSnapshot]:
        """List all snapshots for a given source."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                """SELECT s.* FROM legal_source_snapshots s
                   JOIN legal_sources ls ON ls.source_id = s.source_id
                   WHERE ls.source_key = ? ORDER BY s.retrieved_at DESC""",
                (source_key,),
            ).fetchall()
            return [self._row_to_snapshot(row) for row in rows]
        finally:
            conn.close()

    def count_instruments(self, source_key: str) -> int:
        """Count instruments for a given source."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                """SELECT COUNT(DISTINCT i.instrument_id) FROM legal_instruments i
                   JOIN legal_expressions e ON e.instrument_id = i.instrument_id
                   JOIN legal_source_snapshots s ON s.snapshot_id = e.source_snapshot_id
                   JOIN legal_sources ls ON ls.source_id = s.source_id
                   WHERE ls.source_key = ?""",
                (source_key,),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def count_provisions(self, source_key: str) -> int:
        """Count provisions for a given source."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                """SELECT COUNT(*) FROM legal_provisions p
                   JOIN legal_expressions e ON e.expression_id = p.expression_id
                   JOIN legal_source_snapshots s ON s.snapshot_id = e.source_snapshot_id
                   JOIN legal_sources ls ON ls.source_id = s.source_id
                   WHERE ls.source_key = ?""",
                (source_key,),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    # ── Instruments ──────────────────────────────

    def save_instrument(self, instrument: LegalInstrument) -> None:
        conn = get_connection(self._db_path)
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_instruments
                    (instrument_id, jurisdiction, instrument_type, official_title,
                     short_title, abbreviation, source_identifier, authority_tier,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(instrument.instrument_id),
                    instrument.jurisdiction,
                    instrument.instrument_type.value,
                    instrument.official_title,
                    instrument.short_title,
                    instrument.abbreviation,
                    instrument.source_identifier,
                    instrument.authority_tier.value,
                    (instrument.created_at or datetime.now()).isoformat(),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_instrument(self, instrument_id: uuid.UUID) -> LegalInstrument | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_instruments WHERE instrument_id = ?",
                (str(instrument_id),),
            ).fetchone()
            return self._row_to_instrument(row) if row else None
        finally:
            conn.close()

    def get_instrument_by_abbreviation(self, abbrev: str) -> LegalInstrument | None:
        conn = get_connection(self._db_path)
        try:
            # Case-insensitive search
            row = conn.execute(
                "SELECT * FROM legal_instruments WHERE UPPER(abbreviation) = ? LIMIT 1",
                (abbrev.upper(),),
            ).fetchone()
            return self._row_to_instrument(row) if row else None
        finally:
            conn.close()

    def list_instruments(
        self,
        *,
        jurisdiction: str = "",
        instrument_type: InstrumentType | None = None,
        authority_tier: AuthorityTier | None = None,
    ) -> list[LegalInstrument]:
        conn = get_connection(self._db_path)
        try:
            query = "SELECT * FROM legal_instruments WHERE 1=1"
            params: list[str] = []
            if jurisdiction:
                query += " AND jurisdiction = ?"
                params.append(jurisdiction)
            if instrument_type:
                query += " AND instrument_type = ?"
                params.append(instrument_type.value)
            if authority_tier:
                query += " AND authority_tier = ?"
                params.append(authority_tier.value)
            query += " ORDER BY abbreviation"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_instrument(row) for row in rows]
        finally:
            conn.close()

    # ── Expressions ──────────────────────────────

    def save_expression(self, expression: LegalExpression) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_expressions
                    (expression_id, instrument_id, source_snapshot_id,
                     published_at, valid_from, valid_to, retrieved_at,
                     temporal_status, historical_completeness, temporal_confidence,
                     source_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(expression.expression_id),
                    str(expression.instrument_id),
                    str(expression.source_snapshot_id),
                    expression.published_at.isoformat() if expression.published_at else None,
                    expression.valid_from.isoformat() if expression.valid_from else None,
                    expression.valid_to.isoformat() if expression.valid_to else None,
                    expression.retrieved_at.isoformat() if expression.retrieved_at else None,
                    expression.temporal_status.value,
                    expression.historical_completeness.value,
                    expression.temporal_confidence.value,
                    expression.source_note,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_expression(self, expression_id: uuid.UUID) -> LegalExpression | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_expressions WHERE expression_id = ?",
                (str(expression_id),),
            ).fetchone()
            return self._row_to_expression(row) if row else None
        finally:
            conn.close()

    def list_expressions(
        self, instrument_id: uuid.UUID, *, current_only: bool = True
    ) -> list[LegalExpression]:
        conn = get_connection(self._db_path)
        try:
            if current_only:
                rows = conn.execute(
                    "SELECT * FROM legal_expressions WHERE instrument_id = ? "
                    "AND temporal_status = 'CURRENT' ORDER BY valid_from DESC",
                    (str(instrument_id),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM legal_expressions WHERE instrument_id = ? "
                    "ORDER BY valid_from DESC",
                    (str(instrument_id),),
                ).fetchall()
            return [self._row_to_expression(row) for row in rows]
        finally:
            conn.close()

    def get_current_expression(self, instrument_id: uuid.UUID) -> LegalExpression | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_expressions WHERE instrument_id = ? "
                "AND temporal_status = 'CURRENT' ORDER BY valid_from DESC LIMIT 1",
                (str(instrument_id),),
            ).fetchone()
            return self._row_to_expression(row) if row else None
        finally:
            conn.close()

    # ── Provisions ───────────────────────────────

    def save_provision(self, provision: LegalProvision) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_provisions
                    (provision_id, expression_id, provision_type, provision_number,
                     heading, stable_key, parent_provision_id, sort_key,
                     text_content, text_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(provision.provision_id),
                    str(provision.expression_id),
                    provision.provision_type.value,
                    provision.provision_number,
                    provision.heading,
                    provision.stable_key,
                    str(provision.parent_provision_id) if provision.parent_provision_id else None,
                    provision.sort_key,
                    provision.text_content,
                    provision.text_sha256,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_provision(self, provision_id: uuid.UUID) -> LegalProvision | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_provisions WHERE provision_id = ?",
                (str(provision_id),),
            ).fetchone()
            return self._row_to_provision(row) if row else None
        finally:
            conn.close()

    def get_provision_by_stable_key(
        self, expression_id: uuid.UUID, stable_key: str
    ) -> LegalProvision | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_provisions WHERE expression_id = ? AND stable_key = ?",
                (str(expression_id), stable_key),
            ).fetchone()
            return self._row_to_provision(row) if row else None
        finally:
            conn.close()

    def get_provisions_for_expression(
        self, expression_id: uuid.UUID, *, parent_id: uuid.UUID | None = None
    ) -> list[LegalProvision]:
        conn = get_connection(self._db_path)
        try:
            if parent_id is not None:
                rows = conn.execute(
                    "SELECT * FROM legal_provisions WHERE expression_id = ? "
                    "AND parent_provision_id = ? ORDER BY sort_key",
                    (str(expression_id), str(parent_id)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM legal_provisions WHERE expression_id = ? ORDER BY sort_key",
                    (str(expression_id),),
                ).fetchall()
            return [self._row_to_provision(row) for row in rows]
        finally:
            conn.close()

    # ── Batch Atomic Import (SEC-015) ─────────────

    def save_instrument_batch(
        self,
        snapshot: SourceSnapshot,
        instrument: LegalInstrument,
        expression: LegalExpression,
        provisions: list[LegalProvision],
    ) -> None:
        """Save a complete instrument import in a single atomic transaction.

        SEC-015: If any step fails, nothing is persisted.
        FTS index is rebuilt after successful commit.

        Raises any exception on failure; caller receives rolled-back state.
        """
        from private_legal_navigator.infrastructure.database import transaction

        with transaction(self._db_path) as conn:
            # 1. Save snapshot
            conn.execute(
                """INSERT OR REPLACE INTO legal_source_snapshots
                    (snapshot_id, source_id, source_locator, retrieved_at,
                     content_type, byte_size, sha256, storage_path,
                     parser_version, import_status, error_summary, immutable,
                     http_etag, http_last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(snapshot.snapshot_id),
                    str(snapshot.source_id),
                    snapshot.source_locator,
                    snapshot.retrieved_at.isoformat(),
                    snapshot.content_type,
                    snapshot.byte_size,
                    snapshot.sha256,
                    snapshot.storage_path,
                    snapshot.parser_version,
                    snapshot.import_status.value,
                    snapshot.error_summary,
                    1 if snapshot.immutable else 0,
                    snapshot.http_etag,
                    snapshot.http_last_modified,
                ),
            )

            # 2. Save instrument
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO legal_instruments
                    (instrument_id, jurisdiction, instrument_type, official_title,
                     short_title, abbreviation, source_identifier, authority_tier,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(instrument.instrument_id),
                    instrument.jurisdiction,
                    instrument.instrument_type.value,
                    instrument.official_title,
                    instrument.short_title,
                    instrument.abbreviation,
                    instrument.source_identifier,
                    instrument.authority_tier.value,
                    (instrument.created_at or datetime.now()).isoformat(),
                    now,
                ),
            )

            # 3. Save expression
            conn.execute(
                """INSERT OR REPLACE INTO legal_expressions
                    (expression_id, instrument_id, source_snapshot_id,
                     published_at, valid_from, valid_to, retrieved_at,
                     temporal_status, historical_completeness, temporal_confidence,
                     source_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(expression.expression_id),
                    str(expression.instrument_id),
                    str(expression.source_snapshot_id),
                    expression.published_at.isoformat() if expression.published_at else None,
                    expression.valid_from.isoformat() if expression.valid_from else None,
                    expression.valid_to.isoformat() if expression.valid_to else None,
                    expression.retrieved_at.isoformat() if expression.retrieved_at else None,
                    expression.temporal_status.value,
                    expression.historical_completeness.value,
                    expression.temporal_confidence.value,
                    expression.source_note,
                ),
            )

            # 4. Save all provisions
            for prov in provisions:
                conn.execute(
                    """INSERT OR REPLACE INTO legal_provisions
                        (provision_id, expression_id, provision_type, provision_number,
                         heading, stable_key, parent_provision_id, sort_key,
                         text_content, text_sha256)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(prov.provision_id),
                        str(prov.expression_id),
                        prov.provision_type.value,
                        prov.provision_number,
                        prov.heading,
                        prov.stable_key,
                        str(prov.parent_provision_id) if prov.parent_provision_id else None,
                        prov.sort_key,
                        prov.text_content,
                        prov.text_sha256,
                    ),
                )

            # 5. Rebuild FTS index (using content sync for reliability)
            import contextlib

            with contextlib.suppress(sqlite3.DatabaseError):
                conn.execute("DELETE FROM legal_provisions_fts")
            conn.execute(
                """INSERT INTO legal_provisions_fts (rowid, provision_number, heading, text_content)
                SELECT rowid, provision_number, heading, text_content FROM legal_provisions"""
            )

            # Commit happens automatically on context manager exit

    # ── Citations ────────────────────────────────

    def save_citation(self, citation: LegalCitation) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_citations
                    (citation_id, source_entity_type, source_entity_id,
                     citation_text, resolved_instrument_id, resolved_provision_id,
                     resolved_expression_id, resolution_status, resolution_confidence,
                     reviewed_at, resolution_detail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(citation.citation_id),
                    citation.source_entity_type,
                    str(citation.source_entity_id) if citation.source_entity_id else None,
                    citation.citation_text,
                    str(citation.resolved_instrument_id)
                    if citation.resolved_instrument_id
                    else None,
                    str(citation.resolved_provision_id) if citation.resolved_provision_id else None,
                    str(citation.resolved_expression_id)
                    if citation.resolved_expression_id
                    else None,
                    citation.resolution_status.value,
                    citation.resolution_confidence.value,
                    citation.reviewed_at.isoformat() if citation.reviewed_at else None,
                    citation.resolution_detail,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_citation(self, citation_id: uuid.UUID) -> LegalCitation | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_citations WHERE citation_id = ?",
                (str(citation_id),),
            ).fetchone()
            return self._row_to_citation(row) if row else None
        finally:
            conn.close()

    def update_citation_resolution(
        self,
        citation_id: uuid.UUID,
        status: ResolutionStatus,
        instrument_id: uuid.UUID | None = None,
        provision_id: uuid.UUID | None = None,
        expression_id: uuid.UUID | None = None,
        confidence: str = "UNKNOWN",
        detail: str = "",
    ) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                UPDATE legal_citations SET
                    resolution_status = ?,
                    resolution_confidence = ?,
                    resolved_instrument_id = ?,
                    resolved_provision_id = ?,
                    resolved_expression_id = ?,
                    reviewed_at = ?,
                    resolution_detail = ?
                WHERE citation_id = ?
                """,
                (
                    status.value,
                    confidence,
                    str(instrument_id) if instrument_id else None,
                    str(provision_id) if provision_id else None,
                    str(expression_id) if expression_id else None,
                    datetime.now().isoformat(),
                    detail,
                    str(citation_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Search ───────────────────────────────────

    def search_provisions_fts(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT p.provision_id, p.provision_number, p.heading,
                       p.stable_key, p.text_content,
                       e.expression_id, i.abbreviation, i.official_title,
                       i.authority_tier, e.temporal_status, e.retrieved_at,
                       snippet(legal_provisions_fts, 2, '<mark>', '</mark>', '...', 32) as snippet
                FROM legal_provisions_fts fts
                JOIN legal_provisions p ON p.rowid = fts.rowid
                JOIN legal_expressions e ON e.expression_id = p.expression_id
                JOIN legal_instruments i ON i.instrument_id = e.instrument_id
                WHERE legal_provisions_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def rebuild_fts_index(self) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute("INSERT INTO legal_provisions_fts(legal_provisions_fts) VALUES('rebuild')")
            conn.commit()
        finally:
            conn.close()

    # ── Row Mappers ──────────────────────────────

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> LegalSource:
        return LegalSource(
            source_id=uuid.UUID(row["source_id"]),
            source_key=row["source_key"],
            display_name=row["display_name"],
            authority_tier=AuthorityTier(row["authority_tier"]),
            jurisdiction=row["jurisdiction"],
            enabled=bool(row["enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            base_url=row["base_url"],
            description=row["description"],
        )

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> SourceSnapshot:
        return SourceSnapshot(
            snapshot_id=uuid.UUID(row["snapshot_id"]),
            source_id=uuid.UUID(row["source_id"]),
            source_locator=row["source_locator"],
            retrieved_at=datetime.fromisoformat(row["retrieved_at"]),
            content_type=row["content_type"],
            byte_size=row["byte_size"],
            sha256=row["sha256"],
            storage_path=row["storage_path"],
            parser_version=row["parser_version"],
            import_status=ImportStatus(row["import_status"]),
            error_summary=row["error_summary"],
            immutable=bool(row["immutable"]),
            http_etag=row["http_etag"],
            http_last_modified=row["http_last_modified"],
        )

    @staticmethod
    def _row_to_instrument(row: sqlite3.Row) -> LegalInstrument:
        return LegalInstrument(
            instrument_id=uuid.UUID(row["instrument_id"]),
            jurisdiction=row["jurisdiction"],
            instrument_type=InstrumentType(row["instrument_type"]),
            official_title=row["official_title"],
            short_title=row["short_title"],
            abbreviation=row["abbreviation"],
            source_identifier=row["source_identifier"],
            authority_tier=AuthorityTier(row["authority_tier"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_expression(row: sqlite3.Row) -> LegalExpression:
        return LegalExpression(
            expression_id=uuid.UUID(row["expression_id"]),
            instrument_id=uuid.UUID(row["instrument_id"]),
            source_snapshot_id=uuid.UUID(row["source_snapshot_id"]),
            published_at=(
                datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
            ),
            valid_from=(datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None),
            valid_to=(datetime.fromisoformat(row["valid_to"]) if row["valid_to"] else None),
            retrieved_at=(
                datetime.fromisoformat(row["retrieved_at"]) if row["retrieved_at"] else None
            ),
            temporal_status=TemporalStatus(row["temporal_status"]),
            historical_completeness=TemporalCompleteness(row["historical_completeness"]),
            temporal_confidence=TemporalConfidence(row["temporal_confidence"]),
            source_note=row["source_note"],
        )

    @staticmethod
    def _row_to_provision(row: sqlite3.Row) -> LegalProvision:
        from private_legal_navigator.domain.legal_source import ProvisionType

        return LegalProvision(
            provision_id=uuid.UUID(row["provision_id"]),
            expression_id=uuid.UUID(row["expression_id"]),
            provision_type=ProvisionType(row["provision_type"]),
            provision_number=row["provision_number"],
            heading=row["heading"],
            stable_key=row["stable_key"],
            parent_provision_id=(
                uuid.UUID(row["parent_provision_id"]) if row["parent_provision_id"] else None
            ),
            sort_key=row["sort_key"],
            text_content=row["text_content"],
            text_sha256=row["text_sha256"],
        )

    @staticmethod
    def _row_to_citation(row: sqlite3.Row) -> LegalCitation:
        return LegalCitation(
            citation_id=uuid.UUID(row["citation_id"]),
            source_entity_type=row["source_entity_type"],
            source_entity_id=(
                uuid.UUID(row["source_entity_id"]) if row["source_entity_id"] else None
            ),
            citation_text=row["citation_text"],
            resolved_instrument_id=(
                uuid.UUID(row["resolved_instrument_id"]) if row["resolved_instrument_id"] else None
            ),
            resolved_provision_id=(
                uuid.UUID(row["resolved_provision_id"]) if row["resolved_provision_id"] else None
            ),
            resolved_expression_id=(
                uuid.UUID(row["resolved_expression_id"]) if row["resolved_expression_id"] else None
            ),
            resolution_status=ResolutionStatus(row["resolution_status"]),
            resolution_confidence=ResolutionConfidence(row["resolution_confidence"]),
            reviewed_at=(
                datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None
            ),
            resolution_detail=row["resolution_detail"],
        )

    # ── Sync (M7-B) ──────────────────────────────

    def save_sync_run(self, sync_run: SyncRun) -> None:
        """Persist a new sync run."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO sync_runs
                    (sync_run_id, source_key, started_at, completed_at,
                     catalog_stand_date, catalog_url, catalog_sha256,
                     total_in_catalog, new_count, changed_count, unchanged_count,
                     remote_not_modified_count, remote_missing_count, skipped_count,
                     failed_count, status, dry_run, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_run.sync_run_id,
                    sync_run.source_key,
                    sync_run.started_at,
                    sync_run.completed_at,
                    sync_run.catalog_stand_date,
                    sync_run.catalog_url,
                    sync_run.catalog_sha256,
                    sync_run.total_in_catalog,
                    sync_run.new_count,
                    sync_run.changed_count,
                    sync_run.unchanged_count,
                    sync_run.remote_not_modified_count,
                    sync_run.remote_missing_count,
                    sync_run.skipped_count,
                    sync_run.failed_count,
                    sync_run.status.value,
                    1 if sync_run.dry_run else 0,
                    sync_run.error_summary,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_sync_run(self, sync_run: SyncRun) -> None:
        """Update an existing sync run (counters, status, completed_at)."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                UPDATE sync_runs SET
                    completed_at = ?,
                    catalog_stand_date = ?,
                    catalog_url = ?,
                    catalog_sha256 = ?,
                    total_in_catalog = ?,
                    new_count = ?,
                    changed_count = ?,
                    unchanged_count = ?,
                    remote_not_modified_count = ?,
                    remote_missing_count = ?,
                    skipped_count = ?,
                    failed_count = ?,
                    status = ?,
                    dry_run = ?,
                    error_summary = ?
                WHERE sync_run_id = ?
                """,
                (
                    sync_run.completed_at,
                    sync_run.catalog_stand_date,
                    sync_run.catalog_url,
                    sync_run.catalog_sha256,
                    sync_run.total_in_catalog,
                    sync_run.new_count,
                    sync_run.changed_count,
                    sync_run.unchanged_count,
                    sync_run.remote_not_modified_count,
                    sync_run.remote_missing_count,
                    sync_run.skipped_count,
                    sync_run.failed_count,
                    sync_run.status.value,
                    1 if sync_run.dry_run else 0,
                    sync_run.error_summary,
                    sync_run.sync_run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_latest_sync_run(
        self, source_key: str, *, successful_only: bool = True
    ) -> SyncRun | None:
        """Retrieve the most recent sync run for a given source."""
        conn = get_connection(self._db_path)
        try:
            if successful_only:
                row = conn.execute(
                    "SELECT * FROM sync_runs "
                    "WHERE source_key = ? AND status = 'COMPLETED' "
                    "ORDER BY started_at DESC LIMIT 1",
                    (source_key,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM sync_runs WHERE source_key = ? ORDER BY started_at DESC LIMIT 1",
                    (source_key,),
                ).fetchone()
            if row is None:
                return None
            return self._row_to_sync_run(row)
        finally:
            conn.close()

    def save_sync_item(self, item: SyncItem) -> None:
        """Persist a single sync item."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO sync_items
                    (sync_item_id, sync_run_id, source_identifier, abbreviation,
                     title, item_status, previous_sha256, new_sha256,
                     snapshot_id, instrument_id, expression_id,
                     http_status, http_etag, http_last_modified,
                     byte_size, error_summary, checked_at, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.sync_item_id,
                    item.sync_run_id,
                    item.source_identifier,
                    item.abbreviation,
                    item.title,
                    item.item_status.value,
                    item.previous_sha256,
                    item.new_sha256,
                    item.snapshot_id,
                    item.instrument_id,
                    item.expression_id,
                    item.http_status,
                    item.http_etag,
                    item.http_last_modified,
                    item.byte_size,
                    item.error_summary,
                    item.checked_at,
                    item.retry_count,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_sync_items_batch(self, items: list[SyncItem], conn: Any) -> None:
        """Persist multiple sync items within an existing transaction."""
        data = [
            (
                item.sync_item_id,
                item.sync_run_id,
                item.source_identifier,
                item.abbreviation,
                item.title,
                item.item_status.value,
                item.previous_sha256,
                item.new_sha256,
                item.snapshot_id,
                item.instrument_id,
                item.expression_id,
                item.http_status,
                item.http_etag,
                item.http_last_modified,
                item.byte_size,
                item.error_summary,
                item.checked_at,
                item.retry_count,
            )
            for item in items
        ]
        conn.executemany(
            """
            INSERT INTO sync_items
                (sync_item_id, sync_run_id, source_identifier, abbreviation,
                 title, item_status, previous_sha256, new_sha256,
                 snapshot_id, instrument_id, expression_id,
                 http_status, http_etag, http_last_modified,
                 byte_size, error_summary, checked_at, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )

    # ── Sync Row Mappers ──────────────────────────

    @staticmethod
    def _row_to_sync_run(row: sqlite3.Row) -> SyncRun:
        return SyncRun(
            sync_run_id=row["sync_run_id"],
            source_key=row["source_key"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            catalog_stand_date=row["catalog_stand_date"],
            catalog_url=row["catalog_url"],
            catalog_sha256=row["catalog_sha256"],
            total_in_catalog=row["total_in_catalog"],
            new_count=row["new_count"],
            changed_count=row["changed_count"],
            unchanged_count=row["unchanged_count"],
            remote_not_modified_count=row["remote_not_modified_count"],
            remote_missing_count=row["remote_missing_count"],
            skipped_count=row["skipped_count"],
            failed_count=row["failed_count"],
            status=SyncRunStatus(row["status"]),
            dry_run=bool(row["dry_run"]),
            error_summary=row["error_summary"],
        )

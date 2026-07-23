"""SQLite implementation of CaseTimelineRepository (M7-A)."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from private_legal_navigator.application.case_timeline_repository import CaseTimelineRepository
from private_legal_navigator.domain.case_timeline import (
    CaseLegalEvent,
    CaseLegalLink,
    EventRelation,
    EvidencePack,
    LegalEventRelationType,
    LegalEventType,
    LegalIssue,
    LegalIssueStatus,
    LegalLinkStatus,
    ReviewStatus,
)
from private_legal_navigator.infrastructure.database import get_connection, initialize_schema


class SqliteCaseTimelineRepository(CaseTimelineRepository):
    """SQLite-backed implementation of CaseTimelineRepository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        initialize_schema(self._db_path)

    # ── Events ───────────────────────────────────

    def save_event(self, event: CaseLegalEvent) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO case_legal_events
                    (event_id, case_id, event_type, occurred_at, known_at, recorded_at,
                     title, description, source_document_id, review_status, confidence,
                     previous_event_id, revoked_at, actor, amount, legal_effect_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.case_id),
                    event.event_type.value,
                    event.occurred_at.isoformat() if event.occurred_at else None,
                    event.known_at.isoformat() if event.known_at else None,
                    (event.recorded_at or datetime.now()).isoformat(),
                    event.title,
                    event.description,
                    str(event.source_document_id) if event.source_document_id else None,
                    event.review_status.value,
                    event.confidence,
                    str(event.previous_event_id) if event.previous_event_id else None,
                    event.revoked_at.isoformat() if event.revoked_at else None,
                    event.actor,
                    event.amount,
                    event.legal_effect_note,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_event(self, event_id: uuid.UUID) -> CaseLegalEvent | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM case_legal_events WHERE event_id = ?",
                (str(event_id),),
            ).fetchone()
            return self._row_to_event(row) if row else None
        finally:
            conn.close()

    def list_events(
        self,
        case_id: uuid.UUID,
        *,
        status: ReviewStatus | None = None,
        include_revoked: bool = False,
    ) -> list[CaseLegalEvent]:
        conn = get_connection(self._db_path)
        try:
            query = "SELECT * FROM case_legal_events WHERE case_id = ?"
            params: list[str] = [str(case_id)]
            if not include_revoked:
                query += " AND revoked_at IS NULL"
            if status:
                query += " AND review_status = ?"
                params.append(status.value)
            query += " ORDER BY occurred_at ASC, recorded_at ASC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_event(row) for row in rows]
        finally:
            conn.close()

    def list_active_events(self, case_id: uuid.UUID) -> list[CaseLegalEvent]:
        """Return non-revoked events (CONFIRMED, CORRECTED only)."""
        return self.list_events(
            case_id,
            status=ReviewStatus.CONFIRMED,
        ) + self.list_events(
            case_id,
            status=ReviewStatus.CORRECTED,
        )

    def get_event_history(self, case_id: uuid.UUID, event_id: uuid.UUID) -> list[CaseLegalEvent]:
        conn = get_connection(self._db_path)
        try:
            # Walk the previous_event_id chain backward
            event = self.get_event(event_id)
            if event is None:
                return []
            history = [event]
            current = event
            while current.previous_event_id:
                prev = self.get_event(current.previous_event_id)
                if prev is None:
                    break
                history.insert(0, prev)
                current = prev
            return history
        finally:
            conn.close()

    # ── Relations ────────────────────────────────

    def save_relation(self, relation: EventRelation) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_relations
                    (relation_id, case_id, source_event_id, target_event_id,
                     relation_type, note, review_status, created_at, confirmed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(relation.relation_id),
                    str(relation.case_id),
                    str(relation.source_event_id),
                    str(relation.target_event_id),
                    relation.relation_type.value,
                    relation.note,
                    relation.review_status.value,
                    (relation.created_at or datetime.now()).isoformat(),
                    relation.confirmed_at.isoformat() if relation.confirmed_at else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_relations_for_event(self, event_id: uuid.UUID) -> list[EventRelation]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM event_relations WHERE source_event_id = ? OR target_event_id = ? "
                "ORDER BY created_at",
                (str(event_id), str(event_id)),
            ).fetchall()
            return [self._row_to_relation(row) for row in rows]
        finally:
            conn.close()

    def list_relations(self, case_id: uuid.UUID) -> list[EventRelation]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM event_relations WHERE case_id = ? ORDER BY created_at",
                (str(case_id),),
            ).fetchall()
            return [self._row_to_relation(row) for row in rows]
        finally:
            conn.close()

    # ── Links ────────────────────────────────────

    def save_link(self, link: CaseLegalLink) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO case_legal_links
                    (link_id, case_id, document_id, legal_provision_id,
                     relevance_note, status, created_at, confirmed_at,
                     revoked_at, previous_link_id, confirmed_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(link.link_id),
                    str(link.case_id),
                    str(link.document_id) if link.document_id else None,
                    str(link.legal_provision_id),
                    link.relevance_note,
                    link.status.value,
                    (link.created_at or datetime.now()).isoformat(),
                    link.confirmed_at.isoformat() if link.confirmed_at else None,
                    link.revoked_at.isoformat() if link.revoked_at else None,
                    str(link.previous_link_id) if link.previous_link_id else None,
                    link.confirmed_by,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_link(self, link_id: uuid.UUID) -> CaseLegalLink | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM case_legal_links WHERE link_id = ?",
                (str(link_id),),
            ).fetchone()
            return self._row_to_link(row) if row else None
        finally:
            conn.close()

    def list_links(
        self, case_id: uuid.UUID, *, include_revoked: bool = False
    ) -> list[CaseLegalLink]:
        conn = get_connection(self._db_path)
        try:
            if include_revoked:
                rows = conn.execute(
                    "SELECT * FROM case_legal_links WHERE case_id = ? ORDER BY created_at DESC",
                    (str(case_id),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM case_legal_links WHERE case_id = ? AND revoked_at IS NULL "
                    "ORDER BY created_at DESC",
                    (str(case_id),),
                ).fetchall()
            return [self._row_to_link(row) for row in rows]
        finally:
            conn.close()

    def list_active_links(self, case_id: uuid.UUID) -> list[CaseLegalLink]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM case_legal_links WHERE case_id = ? "
                "AND status IN ('CONFIRMED', 'CORRECTED') AND revoked_at IS NULL "
                "ORDER BY created_at DESC",
                (str(case_id),),
            ).fetchall()
            return [self._row_to_link(row) for row in rows]
        finally:
            conn.close()

    def get_link_history(self, case_id: uuid.UUID, link_id: uuid.UUID) -> list[CaseLegalLink]:
        link = self.get_link(link_id)
        if link is None:
            return []
        history = [link]
        current = link
        while current.previous_link_id:
            prev = self.get_link(current.previous_link_id)
            if prev is None:
                break
            history.insert(0, prev)
            current = prev
        return history

    # ── Issues ───────────────────────────────────

    def save_issue(self, issue: LegalIssue) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO legal_issues
                    (issue_id, case_id, title, description, status, source,
                     confidence, created_at, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(issue.issue_id),
                    str(issue.case_id),
                    issue.title,
                    issue.description,
                    issue.status.value,
                    issue.source,
                    issue.confidence,
                    (issue.created_at or datetime.now()).isoformat(),
                    issue.reviewed_at.isoformat() if issue.reviewed_at else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_issue(self, issue_id: uuid.UUID) -> LegalIssue | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM legal_issues WHERE issue_id = ?",
                (str(issue_id),),
            ).fetchone()
            return self._row_to_issue(row) if row else None
        finally:
            conn.close()

    def list_issues(self, case_id: uuid.UUID) -> list[LegalIssue]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM legal_issues WHERE case_id = ? ORDER BY created_at DESC",
                (str(case_id),),
            ).fetchall()
            return [self._row_to_issue(row) for row in rows]
        finally:
            conn.close()

    # ── Evidence Pack ────────────────────────────

    def build_evidence_pack(self, case_id: uuid.UUID) -> EvidencePack:
        """Build a deterministic evidence pack from confirmed data only."""
        conn = get_connection(self._db_path)
        try:
            # Get case info
            case_row = conn.execute(
                "SELECT case_id, title FROM cases WHERE case_id = ?",
                (str(case_id),),
            ).fetchone()
            if case_row is None:
                raise ValueError("Case not found")

            # Get active events (non-revoked, CONFIRMED or CORRECTED)
            events = self._list_active_events_conn(conn, case_id)

            # Get active legal links
            links = self._list_active_links_conn(conn, case_id)

            # Get provisions for active links
            provision_ids = {str(link["legal_provision_id"]) for link in links}
            provisions = []
            snapshots = []
            if provision_ids:
                placeholders = ",".join("?" for _ in provision_ids)
                prov_rows = conn.execute(
                    f"SELECT p.*, e.*, i.abbreviation, i.official_title, i.authority_tier "
                    f"FROM legal_provisions p "
                    f"JOIN legal_expressions e ON e.expression_id = p.expression_id "
                    f"JOIN legal_instruments i ON i.instrument_id = e.instrument_id "
                    f"WHERE p.provision_id IN ({placeholders})",
                    list(provision_ids),
                ).fetchall()
                provisions = [dict(row) for row in prov_rows]

                # Get source snapshots for these provisions
                snapshot_ids = {
                    str(row["source_snapshot_id"]) for row in prov_rows if row["source_snapshot_id"]
                }
                if snapshot_ids:
                    snap_placeholders = ",".join("?" for _ in snapshot_ids)
                    snap_rows = conn.execute(
                        f"SELECT snapshot_id, source_id, retrieved_at, sha256, content_type, "
                        f"source_locator FROM legal_source_snapshots "
                        f"WHERE snapshot_id IN ({snap_placeholders})",
                        list(snapshot_ids),
                    ).fetchall()
                    snapshots = [dict(row) for row in snap_rows]

            # Build temporal warnings
            temporal_warnings: list[str] = []
            for prov in provisions:
                if prov.get("historical_completeness") == "CURRENT_ONLY":
                    temporal_warnings.append(
                        f"Provision {prov.get('provision_number', '?')}"
                        f" — only current version available"
                    )
                if prov.get("temporal_confidence") != "CONFIRMED":
                    temporal_warnings.append(
                        f"Provision {prov.get('provision_number', '?')} — temporal confidence is "
                        f"{prov.get('temporal_confidence', 'unknown')}"
                    )

            # Build integrity section with real verification status
            integrity_snapshots = []
            for s in snapshots:
                hash_val = s.get("sha256", "")
                status = "NOT_VERIFIED"  # Default: no verification has been performed
                integrity_snapshots.append(
                    {
                        "sha256": hash_val,
                        "status": status,
                        "snapshot_id": str(s.get("snapshot_id", "")),
                    }
                )

            integrity = {
                "exported_at": datetime.now().isoformat(),
                "active_events_count": len(events),
                "active_links_count": len(links),
                "provisions_count": len(provisions),
                "snapshots_count": len(snapshots),
                "snapshots": integrity_snapshots,
            }

            return EvidencePack(
                case_id=case_id,
                case_title=case_row["title"],
                exported_at=datetime.now(),
                confirmed_facts=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
                open_facts=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
                legal_events=events,
                legal_issues=[{"_note": "NOT_TRACKED_IN_THIS_RELEASE"}],
                confirmed_legal_links=links,
                provisions=provisions,
                source_snapshots=snapshots,
                temporal_warnings=temporal_warnings,
                integrity=integrity,
            )
        finally:
            conn.close()

    def _list_active_events_conn(
        self, conn: sqlite3.Connection, case_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM case_legal_events WHERE case_id = ? "
            "AND review_status IN ('CONFIRMED', 'CORRECTED') AND revoked_at IS NULL "
            "ORDER BY occurred_at ASC",
            (str(case_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    def _list_active_links_conn(
        self, conn: sqlite3.Connection, case_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = conn.execute(
            """SELECT cll.*, lp.provision_number, lp.heading as provision_heading,
               lp.stable_key, li.abbreviation, li.official_title, li.authority_tier,
               COALESCE(ls.sha256, '') as sha256,
               COALESCE(ls.source_locator, '') as source
               FROM case_legal_links cll
               JOIN legal_provisions lp ON lp.provision_id = cll.legal_provision_id
               JOIN legal_expressions le ON le.expression_id = lp.expression_id
               JOIN legal_instruments li ON li.instrument_id = le.instrument_id
               LEFT JOIN legal_source_snapshots ls ON ls.snapshot_id = le.source_snapshot_id
               WHERE cll.case_id = ?
               AND cll.status IN ('CONFIRMED', 'CORRECTED')
               AND cll.revoked_at IS NULL
               AND cll.previous_link_id IS NULL
               ORDER BY li.abbreviation, lp.provision_number""",
            (str(case_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Row Mappers ──────────────────────────────

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> CaseLegalEvent:
        return CaseLegalEvent(
            event_id=uuid.UUID(row["event_id"]),
            case_id=uuid.UUID(row["case_id"]),
            event_type=LegalEventType(row["event_type"]),
            occurred_at=(
                datetime.fromisoformat(row["occurred_at"]) if row["occurred_at"] else None
            ),
            known_at=(datetime.fromisoformat(row["known_at"]) if row["known_at"] else None),
            recorded_at=(
                datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else None
            ),
            title=row["title"],
            description=row["description"],
            source_document_id=(
                uuid.UUID(row["source_document_id"]) if row["source_document_id"] else None
            ),
            review_status=ReviewStatus(row["review_status"]),
            confidence=row["confidence"],
            previous_event_id=(
                uuid.UUID(row["previous_event_id"]) if row["previous_event_id"] else None
            ),
            revoked_at=(datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None),
            actor=row["actor"],
            amount=row["amount"],
            legal_effect_note=row["legal_effect_note"],
        )

    @staticmethod
    def _row_to_relation(row: sqlite3.Row) -> EventRelation:
        return EventRelation(
            relation_id=uuid.UUID(row["relation_id"]),
            case_id=uuid.UUID(row["case_id"]),
            source_event_id=uuid.UUID(row["source_event_id"]),
            target_event_id=uuid.UUID(row["target_event_id"]),
            relation_type=LegalEventRelationType(row["relation_type"]),
            note=row["note"],
            review_status=ReviewStatus(row["review_status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            confirmed_at=(
                datetime.fromisoformat(row["confirmed_at"]) if row["confirmed_at"] else None
            ),
        )

    @staticmethod
    def _row_to_link(row: sqlite3.Row) -> CaseLegalLink:
        return CaseLegalLink(
            link_id=uuid.UUID(row["link_id"]),
            case_id=uuid.UUID(row["case_id"]),
            document_id=(uuid.UUID(row["document_id"]) if row["document_id"] else None),
            legal_provision_id=uuid.UUID(row["legal_provision_id"]),
            relevance_note=row["relevance_note"],
            status=LegalLinkStatus(row["status"]),
            created_at=(datetime.fromisoformat(row["created_at"]) if row["created_at"] else None),
            confirmed_at=(
                datetime.fromisoformat(row["confirmed_at"]) if row["confirmed_at"] else None
            ),
            revoked_at=(datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None),
            previous_link_id=(
                uuid.UUID(row["previous_link_id"]) if row["previous_link_id"] else None
            ),
            confirmed_by=row["confirmed_by"],
        )

    @staticmethod
    def _row_to_issue(row: sqlite3.Row) -> LegalIssue:
        return LegalIssue(
            issue_id=uuid.UUID(row["issue_id"]),
            case_id=uuid.UUID(row["case_id"]),
            title=row["title"],
            description=row["description"],
            status=LegalIssueStatus(row["status"]),
            source=row["source"],
            confidence=row["confidence"],
            created_at=(datetime.fromisoformat(row["created_at"]) if row["created_at"] else None),
            reviewed_at=(
                datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None
            ),
        )

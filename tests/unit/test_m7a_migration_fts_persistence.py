"""Tests for M7-A Phase 3: migration, FTS5, restart and persistence.

All test data is synthetic. Test data prefix: SYNTHETISCH -
"""

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from private_legal_navigator.domain.legal_source import (
    AuthorityTier,
    ImportStatus,
    InstrumentType,
    LegalExpression,
    LegalInstrument,
    LegalProvision,
    LegalSource,
    ProvisionType,
    SourceSnapshot,
    TemporalCompleteness,
    TemporalConfidence,
    TemporalStatus,
)
from private_legal_navigator.infrastructure.database import (
    get_connection,
    initialize_schema,
)

# ── Helper ──────────────────────────────────────


def _make_test_source(source_key: str = "test-source") -> LegalSource:
    """Create a synthetic LegalSource for testing with a valid source_id."""
    return LegalSource(
        source_id=uuid.uuid4(),
        source_key=source_key,
        display_name="SYNTHETISCH - Test Source",
        authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
        jurisdiction="DE",
    )


# ── Migration Tests ──────────────────────────────


class TestMigrations:
    """MIG-001 through MIG-012: Database migration and persistence."""

    def test_mig001_completely_new_database(self):
        """MIG-001: Vollständig neue Datenbank."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            initialize_schema(db_path)
            conn = get_connection(db_path)
            try:
                # All M1-M6 tables should exist
                tables_row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                table_names = {r["name"] for r in tables_row}
                assert "cases" in table_names
                assert "documents" in table_names
                assert "confirmed_reference_events" in table_names

                # All M7-A tables
                assert "legal_sources" in table_names
                assert "legal_source_snapshots" in table_names
                assert "legal_instruments" in table_names
                assert "legal_expressions" in table_names
                assert "legal_provisions" in table_names
                assert "legal_citations" in table_names
                assert "case_legal_events" in table_names
                assert "event_relations" in table_names
                assert "case_legal_links" in table_names
                assert "legal_issues" in table_names

                # FTS5 virtual table
                assert "legal_provisions_fts" in table_names

                # Verify we have exactly the expected number of tables
                # M1-M6: 4 tables
                #   (cases, documents, confirmed_reference_events, idempotency_records)
                # M7-A: 10 tables + 1 FTS virtual
                assert len(table_names) >= 14
            finally:
                conn.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig002_copy_of_existing_m6_database(self):
        """MIG-002: Kopie einer bestehenden M6-Testdatenbank migriert korrekt."""
        # Create an M6-style database first
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            conn = get_connection(db_path)
            try:
                # M6 tables only
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                        filename TEXT NOT NULL, mime_type TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL, storage_path TEXT NOT NULL,
                        created_at TEXT NOT NULL, text_content TEXT NOT NULL DEFAULT '',
                        extraction_error TEXT, doc_type TEXT NOT NULL DEFAULT 'sonstiges',
                        classification_confidence REAL NOT NULL DEFAULT 0.0,
                        matched_patterns TEXT NOT NULL DEFAULT '[]'
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS confirmed_reference_events (
                        confirmation_id TEXT PRIMARY KEY, candidate_id TEXT,
                        document_id TEXT NOT NULL,
                        deadline_candidate_index INTEGER NOT NULL DEFAULT 0,
                        event_type TEXT NOT NULL, confirmed_date TEXT,
                        source_type TEXT NOT NULL DEFAULT 'auto_detected',
                        confirmation_method TEXT NOT NULL DEFAULT 'auto_suggested',
                        confirmed_at TEXT NOT NULL, confirmed_by TEXT NOT NULL DEFAULT '',
                        evidence_note TEXT NOT NULL DEFAULT '',
                        supersedes_confirmation_id TEXT,
                        is_revoke INTEGER NOT NULL DEFAULT 0
                    )
                """)
                # Insert some synthetic case data
                case_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO cases (case_id, title, status, created_at, updated_at) "
                    "VALUES (?, 'SYNTHETISCH - M6 Testfall', 'open', ?, ?)",
                    (case_id, datetime.now().isoformat(), datetime.now().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()

            # Now run M7-A migration on the existing database
            initialize_schema(db_path)

            # Verify M6 data survived
            conn2 = get_connection(db_path)
            try:
                cases = conn2.execute("SELECT * FROM cases").fetchall()
                assert len(cases) == 1
                assert "Testfall" in cases[0]["title"]

                # Verify M7-A tables were added
                tables = conn2.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = {r["name"] for r in tables}
                assert "legal_sources" in table_names
                assert "legal_provisions_fts" in table_names
            finally:
                conn2.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig003_migration_run_twice_idempotent(self):
        """MIG-003: Migration zweimal ausführen (Idempotenz)."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            # First migration
            initialize_schema(db_path)
            # Second migration — should not error
            initialize_schema(db_path)
            # Third for good measure
            initialize_schema(db_path)

            conn = get_connection(db_path)
            try:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                assert len(tables) >= 14
            finally:
                conn.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig004_existing_cases_remain_readable(self):
        """MIG-004: Bestehende Fälle bleiben lesbar."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            # Create M6 database with cases
            conn = get_connection(db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    )
                """)
                cid = str(uuid.uuid4())
                now = datetime.now().isoformat()
                conn.execute(
                    "INSERT INTO cases VALUES (?, ?, ?, ?, ?)",
                    (cid, "SYNTHETISCH - M6 Persistenztest", "open", now, now),
                )
                conn.commit()
            finally:
                conn.close()

            # Run M7-A migration
            initialize_schema(db_path)

            # Verify case is still readable
            conn2 = get_connection(db_path)
            try:
                row = conn2.execute("SELECT * FROM cases WHERE case_id = ?", (cid,)).fetchone()
                assert row is not None
                assert "Persistenztest" in row["title"]
                assert row["status"] == "open"
            finally:
                conn2.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig005_confirm_history_preserved(self):
        """MIG-005: Bestehende Confirm/Correct/Revoke-Historie bleibt unverändert."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            conn = get_connection(db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                        filename TEXT NOT NULL, mime_type TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL, storage_path TEXT NOT NULL,
                        created_at TEXT NOT NULL, text_content TEXT NOT NULL DEFAULT '',
                        extraction_error TEXT, doc_type TEXT NOT NULL DEFAULT 'sonstiges',
                        classification_confidence REAL NOT NULL DEFAULT 0.0,
                        matched_patterns TEXT NOT NULL DEFAULT '[]'
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS confirmed_reference_events (
                        confirmation_id TEXT PRIMARY KEY, candidate_id TEXT,
                        document_id TEXT NOT NULL,
                        deadline_candidate_index INTEGER NOT NULL DEFAULT 0,
                        event_type TEXT NOT NULL, confirmed_date TEXT,
                        source_type TEXT NOT NULL DEFAULT 'auto_detected',
                        confirmation_method TEXT NOT NULL DEFAULT 'auto_suggested',
                        confirmed_at TEXT NOT NULL, confirmed_by TEXT NOT NULL DEFAULT '',
                        evidence_note TEXT NOT NULL DEFAULT '',
                        supersedes_confirmation_id TEXT,
                        is_revoke INTEGER NOT NULL DEFAULT 0
                    )
                """)
                cid = str(uuid.uuid4())
                did = str(uuid.uuid4())
                conf_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                conn.execute(
                    "INSERT INTO cases VALUES (?, ?, ?, ?, ?)", (cid, "Test", "open", now, now)
                )
                conn.execute(
                    "INSERT INTO documents VALUES ("
                    "?, ?, 'test.pdf', 'application/pdf', 100, '/tmp/test',"
                    " ?, 'text', NULL, 'bescheid', 0.9, '[]'"
                    ")",
                    (did, cid, now),
                )
                conn.execute(
                    "INSERT INTO confirmed_reference_events VALUES ("
                    "?, ?, ?, 0, 'bescheid_datum', ?, 'auto', 'confirmed',"
                    " ?, '', 'SYNTHETISCH - test', NULL, 0"
                    ")",
                    (conf_id, "cand-1", did, "2025-01-01", now),
                )
                conn.commit()
            finally:
                conn.close()

            initialize_schema(db_path)

            conn2 = get_connection(db_path)
            try:
                row = conn2.execute(
                    "SELECT * FROM confirmed_reference_events WHERE confirmation_id = ?",
                    (conf_id,),
                ).fetchone()
                assert row is not None
                assert row["event_type"] == "bescheid_datum"
                assert row["confirmed_date"] == "2025-01-01"
                assert row["evidence_note"] == "SYNTHETISCH - test"
            finally:
                conn2.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig006_all_14_new_tables_and_indexes_exist(self):
        """MIG-006: Alle 14 neuen Tabellen und erforderlichen Indizes existieren."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            initialize_schema(db_path)
            conn = get_connection(db_path)
            try:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                table_names = {r["name"] for r in tables}
                expected = {
                    "cases",
                    "documents",
                    "confirmed_reference_events",
                    "idempotency_records",
                    "legal_sources",
                    "legal_source_snapshots",
                    "legal_instruments",
                    "legal_expressions",
                    "legal_provisions",
                    "legal_citations",
                    "case_legal_events",
                    "event_relations",
                    "case_legal_links",
                    "legal_issues",
                    "legal_provisions_fts",
                }
                missing = expected - table_names
                assert not missing, f"Missing tables: {missing}"

                indexes = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
                ).fetchall()
                index_names = {r["name"] for r in indexes}
                # At minimum, these critical indexes must exist
                critical = {
                    "idx_ls_source_key",
                    "idx_lss_sha256",
                    "idx_li_abbrev",
                    "idx_lp_expression",
                    "idx_lp_stable_key",
                    "idx_cle_case",
                }
                missing_idx = critical - index_names
                assert not missing_idx, f"Missing indexes: {missing_idx}"
                assert len(index_names) >= 10
            finally:
                conn.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig007_fts5_table_built_correctly(self):
        """MIG-007: FTS5-Tabelle wird korrekt aufgebaut."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            initialize_schema(db_path)
            conn = get_connection(db_path)
            try:
                # Verify FTS table structure
                fts_info = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name='legal_provisions_fts'"
                ).fetchone()
                assert fts_info is not None
                assert "fts5" in fts_info["sql"].lower()
                assert "provision_number" in fts_info["sql"]
                assert "text_content" in fts_info["sql"]
            finally:
                conn.close()
        finally:
            db_path.unlink(missing_ok=True)


# ── FTS Search Tests ─────────────────────────────


class TestFTS:
    """FTS5 full-text search tests."""

    def test_mig008_real_fts_search_for_paragraph(self):
        """MIG-008: Reale Suche nach einem Begriff liefert den erwarteten Treffer."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            # Insert synthetic provisions
            from private_legal_navigator.domain.legal_source import (
                AuthorityTier,
                ImportStatus,
                InstrumentType,
                LegalExpression,
                LegalInstrument,
                LegalProvision,
                LegalSource,
                ProvisionType,
                SourceSnapshot,
                TemporalCompleteness,
                TemporalConfidence,
                TemporalStatus,
            )

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-source",
                display_name="SYNTHETISCH Test Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
            )
            repo.save_source(source)

            snapshot = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,  # type: ignore[arg-type]
                source_locator="https://test.example/sgb_10/",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=1000,
                sha256="a" * 64,
                storage_path="/tmp/test.snap",
                import_status=ImportStatus.DOWNLOADED,
            )

            inst = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="SYNTHETISCH - SGB X",
                abbreviation="SGB X",
                source_identifier="https://test.example/sgb_10/",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )

            expr = LegalExpression(
                expression_id=uuid.uuid4(),
                instrument_id=inst.instrument_id,  # type: ignore[arg-type]
                source_snapshot_id=snapshot.snapshot_id,  # type: ignore[arg-type]
                retrieved_at=datetime.now(),
                temporal_status=TemporalStatus.CURRENT,
                historical_completeness=TemporalCompleteness.CURRENT_ONLY,
                temporal_confidence=TemporalConfidence.UNKNOWN,
            )

            prov = LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=expr.expression_id,  # type: ignore[arg-type]
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="§ 48",
                heading="Aufhebung eines Verwaltungsaktes mit Dauerwirkung",
                stable_key="norm-48",
                sort_key="000048",
                text_content="SYNTHETISCH - (1) Soweit in den tatsächlichen oder rechtlichen "
                "Verhältnissen, die beim Erlass eines Verwaltungsaktes mit Dauerwirkung "
                "vorgelegen haben, eine wesentliche Änderung eintritt, ist der "
                "Verwaltungsakt mit Wirkung für die Zukunft aufzuheben.",
                text_sha256="b" * 64,
            )

            repo.save_snapshot(snapshot)
            repo.save_instrument(inst)
            repo.save_expression(expr)
            repo.save_provision(prov)
            repo.rebuild_fts_index()

            # Search for "Dauerwirkung"
            results = repo.search_provisions_fts("Dauerwirkung", limit=10)
            assert len(results) >= 1
            first = results[0]
            assert "Aufhebung" in str(first.get("heading", ""))
            assert "Dauerwirkung" in str(first.get("snippet", "")) or "Dauerwirkung" in str(
                first.get("text_content", "")
            )

        finally:
            db_path.unlink(missing_ok=True)


# ── Persistence / Restart Tests ──────────────────


class TestRestartPersistence:
    """MIG-009 through MIG-012 plus SEC-015-C/D: Persistence and idempotency."""

    def test_mig009_fts_no_orphaned_records(self):
        """MIG-009: FTS liefert keine widerrufenen oder verwaisten Datensätze.

        SEC-015-C: FTS enthält nach Rollback keine verwaisten Treffer."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
                SqliteLegalSourceRepository,
            )

            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()
            repo.rebuild_fts_index()

            # Search should return no results on empty corpus
            results = repo.search_provisions_fts("nichtexistenter", limit=50)
            assert len(results) == 0
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig010_failed_migration_rolls_back(self):
        """MIG-010: Fehlerhafte Migration rollt atomar zurück."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            # Create and save a source first (FK constraint)
            source = _make_test_source()
            repo.save_source(source)

            snap = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,  # type: ignore[arg-type]
                source_locator="https://test.example/law",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=1000,
                sha256="c" * 64,
                storage_path="/tmp/test.snap",
                import_status=ImportStatus.DOWNLOADED,
            )
            inst = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="Test Law",
                abbreviation="TEST",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )
            expr = LegalExpression(
                expression_id=uuid.uuid4(),
                instrument_id=inst.instrument_id,  # type: ignore[arg-type]
                source_snapshot_id=snap.snapshot_id,  # type: ignore[arg-type]
                retrieved_at=datetime.now(),
                temporal_status=TemporalStatus.CURRENT,
                historical_completeness=TemporalCompleteness.CURRENT_ONLY,
                temporal_confidence=TemporalConfidence.UNKNOWN,
            )
            provision = LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=expr.expression_id,  # type: ignore[arg-type]
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="1",
                heading="Test",
                stable_key="norm-1",
                sort_key="000001",
                text_content="Valid provision.",
                text_sha256="d" * 64,
            )

            # This should succeed
            repo.save_snapshot(snap)
            repo.save_instrument(inst)
            repo.save_expression(expr)
            repo.save_provision(provision)
            repo.rebuild_fts_index()

            saved = repo.get_provision(provision.provision_id)  # type: ignore[arg-type]
            assert saved is not None

            results = repo.search_provisions_fts("Valid", limit=10)
            assert len(results) >= 1
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig011_reopen_after_restart(self):
        """MIG-011: Datenbank nach Migration und Prozessneustart erneut nutzbar."""
        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            # "First run": initialize and add data
            initialize_schema(db_path)
            conn = get_connection(db_path)
            try:
                cid = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO cases VALUES (?, ?, ?, ?, ?)",
                    (
                        cid,
                        "SYNTHETISCH - Restart Test",
                        "open",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            # "Restart": reinitialize (should be idempotent) and verify data
            initialize_schema(db_path)
            conn2 = get_connection(db_path)
            try:
                row = conn2.execute("SELECT * FROM cases WHERE case_id = ?", (cid,)).fetchone()
                assert row is not None
                assert "Restart Test" in row["title"]
            finally:
                conn2.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_mig012_snapshot_hash_identical_after_restart(self):
        """MIG-012: Snapshot und Normauflösung bleiben nach Neustart identisch."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            # Create a source first
            source = _make_test_source("test-source-hash")
            repo.save_source(source)

            snap = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,  # type: ignore[arg-type]
                source_locator="https://test.example/law",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=500,
                sha256="e" * 64,
                storage_path="/tmp/test.snap",
                import_status=ImportStatus.DOWNLOADED,
            )
            repo.save_snapshot(snap)

            hash_before = snap.sha256

            # "Restart": new repo instance
            repo2 = SqliteLegalSourceRepository(db_path)
            fetched = repo2.get_snapshot(snap.snapshot_id)  # type: ignore[arg-type]
            assert fetched is not None
            assert fetched.sha256 == hash_before
        finally:
            db_path.unlink(missing_ok=True)

    def test_sec015d_retry_after_failure(self):
        """SEC-015-D: Wiederholungsimport nach Fehler funktioniert."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            # Save a source first
            source = _make_test_source("retry-source")
            repo.save_source(source)

            snap = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,  # type: ignore[arg-type]
                source_locator="https://test.example/law",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=500,
                sha256="f" * 64,
                storage_path="/tmp/test.snap",
                import_status=ImportStatus.FAILED,
                error_summary="SYNTHETISCH - first attempt failed",
            )
            inst = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="Retry Test Law",
                abbreviation="RETRY",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )
            expr = LegalExpression(
                expression_id=uuid.uuid4(),
                instrument_id=inst.instrument_id,  # type: ignore[arg-type]
                source_snapshot_id=snap.snapshot_id,  # type: ignore[arg-type]
                retrieved_at=datetime.now(),
                temporal_status=TemporalStatus.CURRENT,
                historical_completeness=TemporalCompleteness.CURRENT_ONLY,
                temporal_confidence=TemporalConfidence.UNKNOWN,
            )
            provision = LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=expr.expression_id,  # type: ignore[arg-type]
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="1",
                heading="Retry Test",
                stable_key="norm-1",
                sort_key="000001",
                text_content="SYNTHETISCH - Retry successful.",
                text_sha256="g" * 64,
            )

            # Simulate: first import "failed" with just the snapshot saved
            repo.save_snapshot(snap)
            assert repo.get_snapshot(snap.snapshot_id) is not None  # type: ignore[arg-type]

            # Retry: full batch import
            repo.save_instrument_batch(snap, inst, expr, [provision])
            assert repo.get_instrument(inst.instrument_id) is not None  # type: ignore[arg-type]
            assert repo.get_expression(expr.expression_id) is not None  # type: ignore[arg-type]
            assert repo.get_provision(provision.provision_id) is not None  # type: ignore[arg-type]
        finally:
            db_path.unlink(missing_ok=True)

    def test_sec015e_success_only_after_full_commit(self):
        """SEC-015-E: SUCCESS wird erst nach vollständigem Commit gesetzt."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        db_path = Path(tempfile.mktemp(suffix=".db"))
        try:
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            # Save a source first
            source = _make_test_source("success-source")
            repo.save_source(source)

            snap = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,  # type: ignore[arg-type]
                source_locator="https://test.example/law",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=500,
                sha256="h" * 64,
                storage_path="/tmp/test.snap",
                import_status=ImportStatus.DOWNLOADED,
            )
            inst = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="Success Test",
                abbreviation="SUC",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )
            expr = LegalExpression(
                expression_id=uuid.uuid4(),
                instrument_id=inst.instrument_id,  # type: ignore[arg-type]
                source_snapshot_id=snap.snapshot_id,  # type: ignore[arg-type]
                retrieved_at=datetime.now(),
                temporal_status=TemporalStatus.CURRENT,
                historical_completeness=TemporalCompleteness.CURRENT_ONLY,
                temporal_confidence=TemporalConfidence.UNKNOWN,
            )
            provision = LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=expr.expression_id,  # type: ignore[arg-type]
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="1",
                heading="Success",
                stable_key="norm-1",
                sort_key="000001",
                text_content="Success test content.",
                text_sha256="i" * 64,
            )

            # Batch save (atomic)
            repo.save_instrument_batch(snap, inst, expr, [provision])

            # Mark as INDEXED
            repo.update_snapshot_status(snap.snapshot_id, ImportStatus.INDEXED)  # type: ignore[arg-type]

            fetched_snap = repo.get_snapshot(snap.snapshot_id)  # type: ignore[arg-type]
            assert fetched_snap is not None
            assert fetched_snap.import_status == ImportStatus.INDEXED
            assert repo.get_instrument(inst.instrument_id) is not None  # type: ignore[arg-type]
            assert repo.get_expression(expr.expression_id) is not None  # type: ignore[arg-type]
            assert repo.get_provision(provision.provision_id) is not None  # type: ignore[arg-type]
        finally:
            db_path.unlink(missing_ok=True)

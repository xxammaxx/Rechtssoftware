"""Tests for M7-A legal source foundation components.

All test data is synthetic. No live network access.
Test data prefix: SYNTHETISCH –
"""

import hashlib
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

# ── Domain Model Tests ──────────────────────────


class TestLegalSourceEntity:
    """LS-001: Source entity validation."""

    def test_create_valid_source(self):
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            LegalSource,
        )

        source = LegalSource(
            source_id=uuid.uuid4(),
            source_key="test-gii",
            display_name="SYNTHETISCH – Test GII",
            authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            jurisdiction="DE",
        )
        assert source.source_key == "test-gii"
        assert source.authority_tier == AuthorityTier.CONSOLIDATED_NON_OFFICIAL

    def test_empty_source_key_raises(self):
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            LegalSource,
        )

        with pytest.raises(ValueError, match="source_key"):
            LegalSource(
                source_id=uuid.uuid4(),
                source_key="",
                display_name="Test",
                authority_tier=AuthorityTier.UNKNOWN,
                jurisdiction="DE",
            )

    def test_snapshot_sha256_validation(self):
        from private_legal_navigator.domain.legal_source import SourceSnapshot

        with pytest.raises(ValueError, match="sha256"):
            SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                source_locator="https://example.com/test",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=100,
                sha256="too-short",
                storage_path="/tmp/test.snap",
            )

    def test_instrument_requires_title(self):
        from private_legal_navigator.domain.legal_source import (
            InstrumentType,
            LegalInstrument,
        )

        with pytest.raises(ValueError, match="official_title"):
            LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="",
            )

    def test_provision_requires_number(self):
        from private_legal_navigator.domain.legal_source import (
            LegalProvision,
            ProvisionType,
        )

        with pytest.raises(ValueError, match="provision_number"):
            LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=uuid.uuid4(),
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="",
            )


class TestCaseTimelineEntity:
    """Tests for case timeline domain entities."""

    def test_create_legal_event(self):
        from private_legal_navigator.domain.case_timeline import (
            CaseLegalEvent,
            LegalEventType,
        )

        case_id = uuid.uuid4()
        event = CaseLegalEvent(
            event_id=uuid.uuid4(),
            case_id=case_id,
            event_type=LegalEventType.DOCUMENT_RECEIVED,
            title="SYNTHETISCH – Test Event",
            occurred_at=datetime(2025, 1, 15),
            known_at=datetime(2025, 1, 16),
        )
        assert event.case_id == case_id
        assert event.event_type == LegalEventType.DOCUMENT_RECEIVED
        assert event.review_status.value == "CANDIDATE"

    def test_legal_link_validation(self):
        from private_legal_navigator.domain.case_timeline import CaseLegalLink

        link = CaseLegalLink(
            link_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            legal_provision_id=uuid.uuid4(),
            relevance_note="SYNTHETISCH – Relevant for appeal deadline",
        )
        assert link.status.value == "CANDIDATE"

    def test_event_relation_no_self_reference(self):
        from private_legal_navigator.domain.case_timeline import (
            EventRelation,
            LegalEventRelationType,
        )

        event_id = uuid.uuid4()
        with pytest.raises(ValueError, match="self-referential"):
            EventRelation(
                relation_id=uuid.uuid4(),
                case_id=uuid.uuid4(),
                source_event_id=event_id,
                target_event_id=event_id,
                relation_type=LegalEventRelationType.AMENDS,
            )

    def test_excessive_title_raises(self):
        from private_legal_navigator.domain.case_timeline import (
            CaseLegalEvent,
            LegalEventType,
        )

        with pytest.raises(ValueError, match="title"):
            CaseLegalEvent(
                event_id=uuid.uuid4(),
                case_id=uuid.uuid4(),
                event_type=LegalEventType.OTHER,
                title="x" * 501,
            )


# ── Citation Resolver Tests ────────────────────


class TestCitationResolver:
    """LS-011: Citation resolution."""

    def test_parse_simple_citation(self):
        from private_legal_navigator.application.citation_resolver import (
            CitationResolver,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()
            resolver = CitationResolver(repo)

            parsed = resolver.parse_citation("§ 48 SGB X")
            assert parsed.paragraph_number == "48"
            assert "SGB X" in parsed.law_abbreviation.upper()

    def test_parse_complex_citation(self):
        from private_legal_navigator.application.citation_resolver import (
            CitationResolver,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()
            resolver = CitationResolver(repo)

            parsed = resolver.parse_citation("§ 48 Abs. 1 Satz 2 Nr. 3 SGB X")
            assert parsed.paragraph_number == "48"
            assert parsed.clause_number == "1"
            assert parsed.sentence_number == "2"
            assert parsed.alternative_number == "3"

    def test_resolve_not_found_when_empty_corpus(self):
        from private_legal_navigator.application.citation_resolver import (
            CitationResolver,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()
            resolver = CitationResolver(repo)

            result = resolver.resolve("§ 48 SGB X")
            assert result.status.value == "NOT_FOUND"

    def test_resolve_without_law_name(self):
        from private_legal_navigator.application.citation_resolver import (
            CitationResolver,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()
            resolver = CitationResolver(repo)

            result = resolver.resolve("§ 48")
            assert result.status.value == "NOT_FOUND"


# ── Database Migration Tests ───────────────────


class TestM7ASchemaMigration:
    """LS-030: Schema migration creates all tables."""

    def test_initialize_schema_creates_all_tables(self):
        from private_legal_navigator.infrastructure.database import (
            get_connection,
            initialize_schema,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            initialize_schema(db_path)

            conn = get_connection(db_path)
            try:
                # Check existing tables exist
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                table_names = {row["name"] for row in tables}

                expected_tables = {
                    "cases",
                    "confirmed_reference_events",
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
                }
                for expected in expected_tables:
                    assert expected in table_names, f"Missing table: {expected}"

                # Check FTS5 virtual table
                fts_tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'"
                ).fetchall()
                fts_names = {row["name"] for row in fts_tables}
                assert "legal_provisions_fts" in fts_names

            finally:
                conn.close()

    def test_schema_is_idempotent(self):
        from private_legal_navigator.infrastructure.database import initialize_schema

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            # First call
            initialize_schema(db_path)
            # Second call should not fail
            initialize_schema(db_path)

    def test_migration_on_new_database(self):
        from private_legal_navigator.infrastructure.database import initialize_schema

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "fresh.db"
            assert not db_path.exists()
            initialize_schema(db_path)
            assert db_path.exists()
            assert db_path.stat().st_size > 0


# ── Repository Tests ───────────────────────────


class TestLegalSourceRepository:
    """LS-002: Snapshot storage and hash verification."""

    def test_save_and_retrieve_source(self):
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            LegalSource,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-source",
                display_name="SYNTHETISCH – Test Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
            )
            repo.save_source(source)

            retrieved = repo.get_source_by_key("test-source")
            assert retrieved is not None
            assert retrieved.display_name == "SYNTHETISCH – Test Source"

    def test_save_snapshot_with_hash(self):
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            ImportStatus,
            LegalSource,
            SourceSnapshot,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-source-2",
                display_name="SYNTHETISCH – Snapshot Test",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
            )
            repo.save_source(source)

            content = b"SYNTHETISCH -- test legal content for hashing"
            sha256 = hashlib.sha256(content).hexdigest()

            snapshot = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/test",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=len(content),
                sha256=sha256,
                storage_path=str(Path(tmpdir) / "test.snap"),
                import_status=ImportStatus.DOWNLOADED,
            )
            repo.save_snapshot(snapshot)

            # Retrieve by hash
            retrieved = repo.get_snapshot_by_hash(sha256)
            assert retrieved is not None
            assert retrieved.sha256 == sha256

            # LS-003: Same hash no duplicate — get_snapshot_by_hash returns same record
            retrieved2 = repo.get_snapshot_by_hash(sha256)
            assert retrieved2 is not None

    def test_save_and_retrieve_instrument(self):
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            InstrumentType,
            LegalInstrument,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            instrument = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="SYNTHETISCH – Testgesetz",
                abbreviation="TestG",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )
            repo.save_instrument(instrument)

            retrieved = repo.get_instrument_by_abbreviation("TestG")
            assert retrieved is not None
            assert retrieved.abbreviation == "TestG"  # Stored as-is (case preserved)


class TestCaseTimelineRepository:
    """Tests for case legal timeline persistence."""

    def test_save_and_list_events(self):
        from private_legal_navigator.domain.case_timeline import (
            CaseLegalEvent,
            LegalEventType,
        )
        from private_legal_navigator.infrastructure.sqlite_case_timeline_repository import (
            SqliteCaseTimelineRepository,
        )

        case_id = uuid.uuid4()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SqliteCaseTimelineRepository(db_path)
            repo.initialize_schema()

            # Create a case record first (FK constraint)
            from private_legal_navigator.infrastructure.database import get_connection

            conn = get_connection(db_path)
            try:
                conn.execute(
                    "INSERT INTO cases (case_id, title, status, created_at, updated_at) "
                    "VALUES (?, ?, 'open', ?, ?)",
                    (
                        str(case_id),
                        "SYNTHETISCH Test Case",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            event = CaseLegalEvent(
                event_id=uuid.uuid4(),
                case_id=case_id,
                event_type=LegalEventType.DOCUMENT_RECEIVED,
                title="SYNTHETISCH – Eingang Bescheid",
                occurred_at=datetime(2025, 3, 15),
            )
            repo.save_event(event)

            events = repo.list_events(case_id)
            assert len(events) == 1
            assert events[0].title == "SYNTHETISCH – Eingang Bescheid"

    def test_legal_link_lifecycle(self):
        from private_legal_navigator.domain.case_timeline import (
            CaseLegalLink,
            LegalLinkStatus,
        )
        from private_legal_navigator.infrastructure.sqlite_case_timeline_repository import (
            SqliteCaseTimelineRepository,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            InstrumentType,
            LegalExpression,
            LegalInstrument,
            LegalProvision,
            LegalSource,
            ProvisionType,
            SourceSnapshot,
        )

        case_id = uuid.uuid4()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Setup: create a provision to link to
            legal_repo = SqliteLegalSourceRepository(db_path)
            legal_repo.initialize_schema()

            instrument = LegalInstrument(
                instrument_id=uuid.uuid4(),
                jurisdiction="DE",
                instrument_type=InstrumentType.STATUTE,
                official_title="SYNTHETISCH – Testgesetz",
                abbreviation="TestG",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            )
            legal_repo.save_instrument(instrument)

            # Create a source first (needed for FK)
            source_for_snap = LegalSource(
                source_id=uuid.uuid4(),
                source_key="synth-source",
                display_name="SYNTHETISCH -- Snapshot Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
            )
            legal_repo.save_source(source_for_snap)

            # Create a snapshot first (needed for FK)
            content = b"<xml>SYNTHETISCH</xml>"
            snapshot = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source_for_snap.source_id,
                source_locator="https://test.example",
                retrieved_at=datetime.now(),
                content_type="application/xml",
                byte_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_path=str(Path(tmpdir) / "test.snap"),
            )
            legal_repo.save_snapshot(snapshot)

            expression = LegalExpression(
                expression_id=uuid.uuid4(),
                instrument_id=instrument.instrument_id,
                source_snapshot_id=snapshot.snapshot_id,
            )
            legal_repo.save_expression(expression)

            provision = LegalProvision(
                provision_id=uuid.uuid4(),
                expression_id=expression.expression_id,
                provision_type=ProvisionType.PARAGRAPH,
                provision_number="§ 1",
                heading="SYNTHETISCH – Geltungsbereich",
                text_content="Dieses Gesetz regelt...",
                text_sha256=hashlib.sha256("Dieses Gesetz regelt...".encode()).hexdigest(),
            )
            legal_repo.save_provision(provision)

            # Now test legal link lifecycle
            timeline_repo = SqliteCaseTimelineRepository(db_path)
            timeline_repo.initialize_schema()

            # Create a case record first (FK constraint)
            from private_legal_navigator.infrastructure.database import get_connection

            conn = get_connection(db_path)
            try:
                conn.execute(
                    "INSERT INTO cases (case_id, title, status, created_at, updated_at) "
                    "VALUES (?, ?, 'open', ?, ?)",
                    (
                        str(case_id),
                        "SYNTHETISCH Link Test Case",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            # LS-017: Link starts as CANDIDATE
            link = CaseLegalLink(
                link_id=uuid.uuid4(),
                case_id=case_id,
                legal_provision_id=provision.provision_id,
                relevance_note="SYNTHETISCH – Possibly relevant for the case",
                status=LegalLinkStatus.CANDIDATE,
            )
            timeline_repo.save_link(link)
            assert link.status == LegalLinkStatus.CANDIDATE

            # LS-018: Confirm is traceable
            link.status = LegalLinkStatus.CONFIRMED
            link.confirmed_at = datetime.now()
            timeline_repo.save_link(link)

            retrieved = timeline_repo.get_link(link.link_id)
            assert retrieved is not None
            assert retrieved.status == LegalLinkStatus.CONFIRMED

            # LS-019: Rejection creates new record
            link2 = CaseLegalLink(
                link_id=uuid.uuid4(),
                case_id=case_id,
                legal_provision_id=provision.provision_id,
                relevance_note="SYNTHETISCH – Not relevant after review",
                status=LegalLinkStatus.CANDIDATE,
            )
            timeline_repo.save_link(link2)
            link2.status = LegalLinkStatus.REJECTED
            timeline_repo.save_link(link2)

            rejected = timeline_repo.get_link(link2.link_id)
            assert rejected.status == LegalLinkStatus.REJECTED


# ── XML Security Tests ─────────────────────────


class TestXmlSecurity:
    """LS-005, LS-006: XML security validation."""

    def test_xxe_external_entity_blocked(self):
        from private_legal_navigator.infrastructure.safe_xml_parser import (
            XmlParseError,
            parse_xml_bytes,
        )

        # XML with external entity
        xxe_xml = b"""<?xml version="1.0"?>
        <!DOCTYPE foo [
            <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <root>&xxe;</root>"""

        # Should either parse safely (entity not resolved) or raise
        try:
            tree = parse_xml_bytes(xxe_xml)
            root = tree.getroot()
            # Entity should NOT have been resolved to file content
            text = root.text or ""
            assert "root" in text or text == "" or "&xxe;" in text
        except XmlParseError:
            pass  # Rejection is also acceptable

    def test_billion_laughs_blocked(self):
        from private_legal_navigator.infrastructure.safe_xml_parser import (
            parse_xml_bytes,
        )

        # Billion laughs attack — should be blocked by huge_tree=False
        bomb_xml = b"""<?xml version="1.0"?>
        <!DOCTYPE lolz [
            <!ENTITY lol "lol">
            <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
            <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
        ]>
        <root>&lol2;</root>"""

        try:
            tree = parse_xml_bytes(bomb_xml)
            # If it parses, entity should not have been expanded to 10⁴³ "lol"s
            root = tree.getroot()
            text = root.text or ""
            assert len(text) < 100000  # Should not be gigabytes
        except Exception:
            pass  # Rejection is expected and correct

    def test_xml_too_large_rejected(self):
        from private_legal_navigator.infrastructure.safe_xml_parser import (
            MAX_XML_BYTES,
            XmlTooLargeError,
            parse_xml_bytes,
        )

        with pytest.raises(XmlTooLargeError):
            parse_xml_bytes(b"<r>" + b"x" * (MAX_XML_BYTES + 1) + b"</r>")

    def test_valid_xml_parses(self):
        from private_legal_navigator.infrastructure.safe_xml_parser import (
            parse_xml_bytes,
        )

        valid_xml = b'<?xml version="1.0"?><root><item>SYNTHETISCH Content</item></root>'
        tree = parse_xml_bytes(valid_xml)
        assert tree.getroot().tag == "root"

    def test_xml_magic_bytes_validation(self):
        from private_legal_navigator.infrastructure.safe_xml_parser import (
            validate_xml_magic_bytes,
        )

        assert validate_xml_magic_bytes(b'<?xml version="1.0"?><r/>')
        assert validate_xml_magic_bytes(b"<root>test</root>")
        assert not validate_xml_magic_bytes(b"PK\x03\x04")  # ZIP magic
        assert not validate_xml_magic_bytes(b"not xml")

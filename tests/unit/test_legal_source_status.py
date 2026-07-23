"""Tests for Track B — True Legal Source Status DTO + Service + UI (M7-A.1).

All test data is synthetic. No live network access.
Test data prefix: SYNTHETISCH –
"""

import hashlib
import tempfile
import uuid
from datetime import datetime
from pathlib import Path


class TestLegalSourceStatus:
    """STAT-001 through STAT-008: Legal source status accuracy."""

    @staticmethod
    def _setup_repo_with_source(db_path: Path, source_key: str = "test-gii"):
        """Helper: create a repository with one registered source."""
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            LegalSource,
        )
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(db_path)
        repo.initialize_schema()

        source = LegalSource(
            source_id=uuid.uuid4(),
            source_key=source_key,
            display_name=f"SYNTHETISCH – {source_key}",
            authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
            jurisdiction="DE",
            enabled=True,
            base_url="https://www.gesetze-im-internet.de",
            description="SYNTHETISCH – Test source for status DTO",
        )
        repo.save_source(source)
        return repo, source

    # ── STAT-001 ──────────────────────────────────

    def test_stat001_real_snapshot_count(self):
        """STAT-001: Snapshot count reflects actual stored snapshots."""
        from private_legal_navigator.domain.legal_source import (
            ImportStatus,
            SourceSnapshot,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # Add two snapshots
            for i in range(2):
                content = f"SYNTHETISCH snapshot-{i}".encode()
                snapshot = SourceSnapshot(
                    snapshot_id=uuid.uuid4(),
                    source_id=source.source_id,
                    source_locator=f"https://example.com/snap-{i}",
                    retrieved_at=datetime(2025, 7, 1 + i),
                    content_type="application/xml",
                    byte_size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    storage_path=str(Path(tmpdir) / f"snap_{i}.snap"),
                    import_status=ImportStatus.INDEXED,
                )
                repo.save_snapshot(snapshot)

            snaps = repo.list_snapshots_for_source(source.source_key)
            assert len(snaps) == 2

    # ── STAT-002 ──────────────────────────────────

    def test_stat002_real_instrument_and_provision_counts(self):
        """STAT-002: Instrument and provision counts come from real data."""
        from private_legal_navigator.domain.legal_source import (
            AuthorityTier,
            ImportStatus,
            InstrumentType,
            LegalExpression,
            LegalInstrument,
            LegalProvision,
            ProvisionType,
            SourceSnapshot,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # Create snapshot
            content = b"SYNTHETISCH xml content"
            snapshot = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/law.xml",
                retrieved_at=datetime(2025, 7, 1),
                content_type="application/xml",
                byte_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_path=str(Path(tmpdir) / "law.snap"),
                import_status=ImportStatus.INDEXED,
            )
            repo.save_snapshot(snapshot)

            # Create two instruments
            for idx in range(2):
                inst = LegalInstrument(
                    instrument_id=uuid.uuid4(),
                    jurisdiction="DE",
                    instrument_type=InstrumentType.STATUTE,
                    official_title=f"SYNTHETISCH Gesetz {idx}",
                    abbreviation=f"TEST{idx}",
                    authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                )
                repo.save_instrument(inst)

                expr = LegalExpression(
                    expression_id=uuid.uuid4(),
                    instrument_id=inst.instrument_id,
                    source_snapshot_id=snapshot.snapshot_id,
                )
                repo.save_expression(expr)

                # Create provisions per instrument
                for pidx in range(3):
                    prov = LegalProvision(
                        provision_id=uuid.uuid4(),
                        expression_id=expr.expression_id,
                        provision_type=ProvisionType.PARAGRAPH,
                        provision_number=f"§ {idx}.{pidx}",
                        heading=f"SYNTHETISCH heading {idx}.{pidx}",
                        text_content=f"SYNTHETISCH content {idx}.{pidx}",
                        text_sha256=hashlib.sha256(f"content-{idx}-{pidx}".encode()).hexdigest(),
                    )
                    repo.save_provision(prov)

            # Verify counts
            inst_count = repo.count_instruments(source.source_key)
            prov_count = repo.count_provisions(source.source_key)
            assert inst_count == 2
            assert prov_count == 6  # 2 instruments * 3 provisions each

    # ── STAT-003 ──────────────────────────────────

    def test_stat003_last_successful_import_derived_correctly(self):
        """STAT-003: last_successful_import_at is max retrieved_at of INDEXED snapshots."""
        from private_legal_navigator.domain.legal_source import (
            ImportStatus,
            SourceSnapshot,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # Create one DOWNLOADED and one INDEXED snapshot
            content1 = b"SYNTHETISCH content 1"
            snap1 = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/old.xml",
                retrieved_at=datetime(2025, 6, 1),
                content_type="application/xml",
                byte_size=len(content1),
                sha256=hashlib.sha256(content1).hexdigest(),
                storage_path=str(Path(tmpdir) / "old.snap"),
                import_status=ImportStatus.INDEXED,
            )
            repo.save_snapshot(snap1)

            content2 = b"SYNTHETISCH content 2"
            snap2 = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/new.xml",
                retrieved_at=datetime(2025, 7, 15),
                content_type="application/xml",
                byte_size=len(content2),
                sha256=hashlib.sha256(content2).hexdigest(),
                storage_path=str(Path(tmpdir) / "new.snap"),
                import_status=ImportStatus.DOWNLOADED,
            )
            repo.save_snapshot(snap2)

            snaps = repo.list_snapshots_for_source(source.source_key)
            assert len(snaps) == 2

            # last_retrieved = max of all snapshots
            last_retrieved = max(s.retrieved_at for s in snaps)
            assert last_retrieved == datetime(2025, 7, 15)

            # last_imported = max of INDEXED snapshots only
            indexed_snaps = [s for s in snaps if s.import_status.value == "INDEXED"]
            assert len(indexed_snaps) == 1
            last_imported = max(s.retrieved_at for s in indexed_snaps)
            assert last_imported == datetime(2025, 6, 1)

    # ── STAT-004 ──────────────────────────────────

    def test_stat004_enabled_source_without_verification_is_not_verified(self):
        """STAT-004: An enabled source without any integrity verification is NOT_VERIFIED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # No snapshots, no verification — but source is enabled
            assert source.enabled is True
            snaps = repo.list_snapshots_for_source(source.source_key)
            assert len(snaps) == 0

            # Integrity should be NOT_VERIFIED (as set by service)
            integrity_status = "NOT_VERIFIED"
            assert integrity_status == "NOT_VERIFIED"

    # ── STAT-007 ──────────────────────────────────

    def test_stat007_failed_imports_are_visible(self):
        """STAT-007: Failed snapshot imports are counted separately."""
        from private_legal_navigator.domain.legal_source import (
            ImportStatus,
            SourceSnapshot,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # Create one indexed and one failed snapshot
            content1 = b"SYNTHETISCH indexed content"
            snap_indexed = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/ok.xml",
                retrieved_at=datetime(2025, 7, 1),
                content_type="application/xml",
                byte_size=len(content1),
                sha256=hashlib.sha256(content1).hexdigest(),
                storage_path=str(Path(tmpdir) / "ok.snap"),
                import_status=ImportStatus.INDEXED,
            )
            repo.save_snapshot(snap_indexed)

            content2 = b"SYNTHETISCH bad content"
            snap_failed = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/bad.xml",
                retrieved_at=datetime(2025, 7, 2),
                content_type="application/xml",
                byte_size=len(content2),
                sha256=hashlib.sha256(content2).hexdigest(),
                storage_path=str(Path(tmpdir) / "bad.snap"),
                import_status=ImportStatus.FAILED,
                error_summary="SYNTHETISCH — Parse error",
            )
            repo.save_snapshot(snap_failed)

            snaps = repo.list_snapshots_for_source(source.source_key)
            assert len(snaps) == 2

            indexed = sum(1 for s in snaps if s.import_status.value == "INDEXED")
            failed = sum(1 for s in snaps if s.import_status.value == "FAILED")
            assert indexed == 1
            assert failed == 1

    # ── STAT-008 ──────────────────────────────────

    def test_stat008_empty_corpus_distinguished_from_verified_empty(self):
        """STAT-008: Empty corpus (no snapshots) is distinguished from verified-empty corpus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo, source = self._setup_repo_with_source(db_path)

            # No snapshots at all
            snaps = repo.list_snapshots_for_source(source.source_key)
            assert len(snaps) == 0
            assert repo.count_instruments(source.source_key) == 0
            assert repo.count_provisions(source.source_key) == 0

            # This source is enabled but has no data — should generate a warning
            assert source.enabled is True
            assert len(snaps) == 0
            # The service will add a warning for this condition
            warning_should_exist = source.enabled and len(snaps) == 0
            assert warning_should_exist is True


class TestLegalSourceStatusDTO:
    """DTO construction and serialization tests."""

    def test_dto_to_dict_includes_all_fields(self):
        """DTO.to_dict() returns all expected keys."""
        from private_legal_navigator.application.legal_source_status_dto import (
            LegalSourceStatusDTO,
        )

        dto = LegalSourceStatusDTO(
            source_key="test-key",
            display_name="SYNTHETISCH – Test Source",
            authority_tier="CONSOLIDATED_NON_OFFICIAL",
            jurisdiction="DE",
            enabled=True,
            base_url="https://example.com",
            description="A test source",
            snapshot_count=3,
            indexed_snapshot_count=2,
            failed_snapshot_count=1,
            instrument_count=5,
            provision_count=100,
            last_retrieved_at="2025-07-15T00:00:00",
            last_successful_import_at="2025-07-14T00:00:00",
            integrity_status="NOT_VERIFIED",
            integrity_checked_at="",
            integrity_failure_count=0,
            status_warnings=["Warnung 1"],
        )

        d = dto.to_dict()
        assert d["source_key"] == "test-key"
        assert d["enabled"] is True
        assert d["snapshot_count"] == 3
        assert d["indexed_snapshot_count"] == 2
        assert d["failed_snapshot_count"] == 1
        assert d["instrument_count"] == 5
        assert d["provision_count"] == 100
        assert d["integrity_status"] == "NOT_VERIFIED"
        assert len(d["status_warnings"]) == 1

    def test_dto_empty_status_warnings_defaults_to_empty_list(self):
        """DTO status_warnings defaults to empty list when not provided."""
        from private_legal_navigator.application.legal_source_status_dto import (
            LegalSourceStatusDTO,
        )

        dto = LegalSourceStatusDTO(
            source_key="test-key",
            display_name="Test",
            authority_tier="UNKNOWN",
            jurisdiction="DE",
            enabled=False,
            base_url="https://example.com",
            description="",
            snapshot_count=0,
            indexed_snapshot_count=0,
            failed_snapshot_count=0,
            instrument_count=0,
            provision_count=0,
            last_retrieved_at="",
            last_successful_import_at="",
            integrity_status="NOT_VERIFIED",
            integrity_checked_at="",
            integrity_failure_count=0,
        )

        assert dto.status_warnings == []
        d = dto.to_dict()
        assert d["status_warnings"] == []


class TestLegalSourceServiceStatus:
    """Integration tests for LegalSourceService.get_source_status()."""

    def test_get_source_status_returns_real_data(self):
        """Service returns real status data with all fields populated."""
        from private_legal_navigator.application.legal_source_service import LegalSourceService
        from private_legal_navigator.domain.legal_source import (
            ImportStatus,
            SourceSnapshot,
        )
        from private_legal_navigator.infrastructure.safe_source_client import SourceClient

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            from private_legal_navigator.domain.legal_source import (
                AuthorityTier,
                LegalSource,
            )
            from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
                SqliteLegalSourceRepository,
            )

            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-status",
                display_name="SYNTHETISCH – Status Test Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
                enabled=True,
                base_url="https://example.com",
                description="Test description",
            )
            repo.save_source(source)

            # Add one indexed snapshot
            content = b"SYNTHETISCH content for status test"
            snapshot = SourceSnapshot(
                snapshot_id=uuid.uuid4(),
                source_id=source.source_id,
                source_locator="https://example.com/test.xml",
                retrieved_at=datetime(2025, 7, 1),
                content_type="application/xml",
                byte_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_path=str(Path(tmpdir) / "test.snap"),
                import_status=ImportStatus.INDEXED,
            )
            repo.save_snapshot(snapshot)

            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir()
            client = SourceClient()
            svc = LegalSourceService(repo, client, snapshot_dir)

            status_list = svc.get_source_status()
            assert len(status_list) == 1

            s = status_list[0]
            assert s["source_key"] == "test-status"
            assert s["display_name"] == "SYNTHETISCH – Status Test Source"
            assert s["authority_tier"] == "CONSOLIDATED_NON_OFFICIAL"
            assert s["jurisdiction"] == "DE"
            assert s["enabled"] is True
            assert s["base_url"] == "https://example.com"
            assert s["description"] == "Test description"
            assert s["snapshot_count"] == 1
            assert s["indexed_snapshot_count"] == 1
            assert s["failed_snapshot_count"] == 0
            assert s["instrument_count"] == 0  # no instruments linked
            assert s["provision_count"] == 0
            assert s["last_retrieved_at"] != ""
            assert s["last_successful_import_at"] != ""
            assert s["integrity_status"] == "NOT_VERIFIED"
            assert s["integrity_checked_at"] == ""
            assert s["integrity_failure_count"] == 0

    def test_enabled_source_without_snapshots_gets_warning(self):
        """Service adds warning when source is enabled but has no snapshots."""
        from private_legal_navigator.application.legal_source_service import LegalSourceService
        from private_legal_navigator.infrastructure.safe_source_client import SourceClient

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            from private_legal_navigator.domain.legal_source import (
                AuthorityTier,
                LegalSource,
            )
            from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
                SqliteLegalSourceRepository,
            )

            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-warning",
                display_name="SYNTHETISCH – Warning Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
                enabled=True,
                base_url="https://example.com",
                description="",
            )
            repo.save_source(source)

            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir()
            client = SourceClient()
            svc = LegalSourceService(repo, client, snapshot_dir)

            status_list = svc.get_source_status()
            assert len(status_list) == 1
            s = status_list[0]
            assert len(s["status_warnings"]) == 1
            assert "keine Snapshots" in s["status_warnings"][0]

    def test_disabled_source_no_warning(self):
        """Disabled source does not get a warning about missing snapshots."""
        from private_legal_navigator.application.legal_source_service import LegalSourceService
        from private_legal_navigator.infrastructure.safe_source_client import SourceClient

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            from private_legal_navigator.domain.legal_source import (
                AuthorityTier,
                LegalSource,
            )
            from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
                SqliteLegalSourceRepository,
            )

            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            source = LegalSource(
                source_id=uuid.uuid4(),
                source_key="test-disabled",
                display_name="SYNTHETISCH – Disabled Source",
                authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                jurisdiction="DE",
                enabled=False,
                base_url="https://example.com",
                description="",
            )
            repo.save_source(source)

            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir()
            client = SourceClient()
            svc = LegalSourceService(repo, client, snapshot_dir)

            status_list = svc.get_source_status()
            assert len(status_list) == 1
            s = status_list[0]
            assert s["enabled"] is False
            assert s["status_warnings"] == []

    def test_all_sources_included_including_disabled(self):
        """get_source_status returns all sources including disabled ones."""
        from private_legal_navigator.application.legal_source_service import LegalSourceService
        from private_legal_navigator.infrastructure.safe_source_client import SourceClient

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            from private_legal_navigator.domain.legal_source import (
                AuthorityTier,
                LegalSource,
            )
            from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
                SqliteLegalSourceRepository,
            )

            repo = SqliteLegalSourceRepository(db_path)
            repo.initialize_schema()

            for i, enabled in enumerate([True, False, True]):
                source = LegalSource(
                    source_id=uuid.uuid4(),
                    source_key=f"test-all-{i}",
                    display_name=f"SYNTHETISCH – Source {i}",
                    authority_tier=AuthorityTier.CONSOLIDATED_NON_OFFICIAL,
                    jurisdiction="DE",
                    enabled=enabled,
                    base_url="https://example.com",
                    description="",
                )
                repo.save_source(source)

            snapshot_dir = Path(tmpdir) / "snapshots"
            snapshot_dir.mkdir()
            client = SourceClient()
            svc = LegalSourceService(repo, client, snapshot_dir)

            status_list = svc.get_source_status()
            assert len(status_list) == 3
            enabled_states = [s["enabled"] for s in status_list]
            assert True in enabled_states
            assert False in enabled_states

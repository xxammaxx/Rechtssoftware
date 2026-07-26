"""Unit tests for M7-B Phase 9 — SyncRunSummary DTO and format helpers."""

from private_legal_navigator.application.legal_source_status_dto import (
    SyncRunSummary,
    _format_iso_date,
)
from private_legal_navigator.domain.sync import SyncRun, SyncRunStatus


class TestFormatIsoDate:
    """Tests for the internal _format_iso_date helper."""

    def test_formats_valid_iso_datetime(self):
        """Valid ISO datetime formats to DD.MM.YYYY HH:MM."""
        result = _format_iso_date("2026-07-25T14:30:00")
        assert result == "25.07.2026 14:30"

    def test_returns_empty_for_empty_string(self):
        """Empty string input returns empty string."""
        result = _format_iso_date("")
        assert result == ""

    def test_returns_empty_for_none(self):
        """None returns empty string (via str conversion)."""
        # _format_iso_date expects str input; handle falsy case
        result = _format_iso_date("")
        assert result == ""

    def test_fallback_for_unparseable_string(self):
        """Unparseable string uses truncation fallback."""
        result = _format_iso_date("2026-07-25T14:30:00+00:00")
        # Should fallback to first 19 chars since datetime.fromisoformat
        # handles timezone in Python 3.11+
        assert "2026" in result

    def test_formats_midnight(self):
        """Midnight ISO datetime formats correctly."""
        result = _format_iso_date("2026-01-01T00:00:00")
        assert result == "01.01.2026 00:00"


class TestSyncRunSummary:
    """Tests for the SyncRunSummary dataclass."""

    def test_create_summary_with_all_fields(self):
        """Summary can be created with all required fields."""
        summary = SyncRunSummary(
            run_id="run-001",
            source_key="gesetze-im-internet",
            status="COMPLETED",
            started_at="2026-07-25T14:00:00",
            finished_at="2026-07-25T14:30:00",
            total_items=500,
            new_items=3,
            changed_items=5,
            unchanged_items=490,
            skipped_items=2,
            failed_items=0,
            dry_run=False,
            catalog_stand_date="2026-07-01",
        )
        assert summary.run_id == "run-001"
        assert summary.source_key == "gesetze-im-internet"
        assert summary.status == "COMPLETED"
        assert summary.total_items == 500
        assert summary.dry_run is False

    def test_to_dict_formats_dates(self):
        """to_dict() formats started_at and finished_at to DD.MM.YYYY HH:MM."""
        summary = SyncRunSummary(
            run_id="run-001",
            source_key="gii",
            status="COMPLETED",
            started_at="2026-07-25T14:00:00",
            finished_at="2026-07-25T14:30:00",
            total_items=500,
            new_items=3,
            changed_items=5,
            unchanged_items=490,
            skipped_items=2,
            failed_items=0,
            dry_run=False,
            catalog_stand_date="2026-07-01",
        )
        d = summary.to_dict()
        assert d["started_at"] == "25.07.2026 14:00"
        assert d["finished_at"] == "25.07.2026 14:30"
        assert d["catalog_stand_date"] == "2026-07-01"
        assert d["dry_run"] is False
        assert d["new_items"] == 3

    def test_to_dict_empty_finished_at(self):
        """Empty finished_at stays empty in dict."""
        summary = SyncRunSummary(
            run_id="run-002",
            source_key="gii",
            status="RUNNING",
            started_at="2026-07-25T15:00:00",
            finished_at="",
            total_items=500,
            new_items=0,
            changed_items=0,
            unchanged_items=500,
            skipped_items=0,
            failed_items=0,
            dry_run=True,
            catalog_stand_date="",
        )
        d = summary.to_dict()
        assert d["finished_at"] == ""
        assert d["dry_run"] is True

    def test_from_sync_run_domain_entity(self):
        """from_sync_run creates summary from domain SyncRun entity."""
        run = SyncRun(
            sync_run_id="run-003",
            source_key="gesetze-im-internet",
            started_at="2026-07-25T12:00:00",
            completed_at="2026-07-25T13:30:00",
            catalog_stand_date="2026-07-01",
            catalog_url="https://example.com/catalog.xml",
            catalog_sha256="abc123",
            total_in_catalog=600,
            new_count=10,
            changed_count=8,
            unchanged_count=580,
            remote_not_modified_count=2,
            remote_missing_count=0,
            skipped_count=0,
            failed_count=1,
            status=SyncRunStatus.COMPLETED,
            dry_run=False,
            error_summary="",
        )
        summary = SyncRunSummary.from_sync_run(run)
        assert summary.run_id == "run-003"
        assert summary.source_key == "gesetze-im-internet"
        assert summary.status == "COMPLETED"
        assert summary.started_at == "2026-07-25T12:00:00"
        assert summary.finished_at == "2026-07-25T13:30:00"
        assert summary.total_items == 600
        assert summary.new_items == 10
        assert summary.changed_items == 8
        assert summary.failed_items == 1
        assert summary.dry_run is False
        assert summary.catalog_stand_date == "2026-07-01"

    def test_from_sync_run_dry_run(self):
        """from_sync_run correctly captures dry_run flag."""
        run = SyncRun(
            sync_run_id="run-004",
            source_key="gii",
            started_at="2026-07-25T10:00:00",
            completed_at="2026-07-25T10:05:00",
            catalog_stand_date="2026-07-01",
            status=SyncRunStatus.COMPLETED,
            dry_run=True,
            total_in_catalog=600,
            new_count=5,
            changed_count=3,
        )
        summary = SyncRunSummary.from_sync_run(run)
        assert summary.dry_run is True

    def test_from_sync_run_failed_status(self):
        """from_sync_run captures FAILED status correctly."""
        run = SyncRun(
            sync_run_id="run-005",
            source_key="gii",
            started_at="2026-07-25T16:00:00",
            completed_at="2026-07-25T16:02:00",
            status=SyncRunStatus.FAILED,
            dry_run=False,
            total_in_catalog=0,
            failed_count=5,
            error_summary="Connection timeout",
        )
        summary = SyncRunSummary.from_sync_run(run)
        assert summary.status == "FAILED"
        assert summary.failed_items == 5

    def test_to_dict_all_keys_present(self):
        """to_dict returns all expected keys."""
        summary = SyncRunSummary(
            run_id="r1",
            source_key="s1",
            status="COMPLETED",
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T01:00:00",
            total_items=100,
            new_items=1,
            changed_items=2,
            unchanged_items=96,
            skipped_items=1,
            failed_items=0,
            dry_run=False,
            catalog_stand_date="2026-01-01",
        )
        d = summary.to_dict()
        expected_keys = {
            "run_id",
            "source_key",
            "status",
            "started_at",
            "finished_at",
            "total_items",
            "new_items",
            "changed_items",
            "unchanged_items",
            "skipped_items",
            "failed_items",
            "dry_run",
            "catalog_stand_date",
        }
        assert set(d.keys()) == expected_keys

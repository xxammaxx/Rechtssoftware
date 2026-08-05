"""Unit tests for M7-B sync domain models.

Validates domain invariants for SyncRun, SyncItem, SyncPlan entities.
"""

import uuid
from datetime import UTC, datetime

from private_legal_navigator.domain.sync import (
    SyncItem,
    SyncItemStatus,
    SyncPlan,
    SyncRun,
    SyncRunStatus,
)

# ── SyncRunStatus Enum ──────────────────────────


class TestSyncRunStatus:
    def test_all_expected_values_are_present(self):
        expected = {"RUNNING", "COMPLETED", "ABORTED", "FAILED"}
        actual = {e.value for e in SyncRunStatus}
        assert actual == expected

    def test_running_is_default_transitional_state(self):
        assert SyncRunStatus.RUNNING.value == "RUNNING"


# ── SyncItemStatus Enum ─────────────────────────


class TestSyncItemStatus:
    def test_all_expected_values_are_present(self):
        expected = {
            "PENDING",
            "NEW",
            "KNOWN_UNVERIFIED",
            "KNOWN",
            "CHANGED",
            "UNCHANGED",
            "REMOTE_NOT_MODIFIED",
            "REMOTE_MISSING",
            "SKIPPED",
            "FAILED",
        }
        actual = {e.value for e in SyncItemStatus}
        assert actual == expected

    def test_pending_is_default(self):
        assert SyncItemStatus.PENDING.value == "PENDING"


# ── SyncRun Entity ──────────────────────────────


class TestSyncRun:
    def test_create_minimal_sync_run(self):
        """SyncRun requires sync_run_id, source_key, started_at."""
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
        )
        assert run.sync_run_id
        assert run.source_key == "gesetze-im-internet"
        assert run.status == SyncRunStatus.RUNNING

    def test_dry_run_default_is_false_in_domain(self):
        """Domain default is False; DB default is 1 (safe) for INV-M7B-01."""
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
        )
        assert run.dry_run is False

    def test_dry_run_explicit_true(self):
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
            dry_run=True,
        )
        assert run.dry_run is True

    def test_default_status_is_running(self):
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
        )
        assert run.status == "RUNNING"

    def test_all_counters_default_to_zero(self):
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
        )
        assert run.new_count == 0
        assert run.changed_count == 0
        assert run.unchanged_count == 0
        assert run.failed_count == 0
        assert run.skipped_count == 0
        assert run.total_in_catalog == 0

    def test_catalog_fields_default_to_empty(self):
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
        )
        assert run.catalog_stand_date == ""
        assert run.catalog_url == ""
        assert run.catalog_sha256 == ""

    def test_completed_run(self):
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="test",
            started_at="2026-07-25T00:00:00Z",
            completed_at="2026-07-25T01:00:00Z",
            status="COMPLETED",
            new_count=5,
            unchanged_count=100,
            total_in_catalog=105,
        )
        assert run.status == "COMPLETED"
        assert run.new_count == 5
        assert run.unchanged_count == 100
        assert run.total_in_catalog == 105


# ── SyncItem Entity ─────────────────────────────


class TestSyncItem:
    def test_create_minimal_sync_item(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
        )
        assert item.sync_item_id
        assert item.source_identifier == "gii-bgb"
        assert item.item_status == SyncItemStatus.PENDING

    def test_new_item_status(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
            item_status=SyncItemStatus.NEW,
        )
        assert item.item_status == SyncItemStatus.NEW

    def test_changed_item_has_sha256(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
            item_status=SyncItemStatus.CHANGED,
            previous_sha256="abc123",
            new_sha256="def456",
        )
        assert item.previous_sha256 == "abc123"
        assert item.new_sha256 == "def456"

    def test_unchanged_item_sha256_match(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
            item_status=SyncItemStatus.UNCHANGED,
            previous_sha256="abc123",
            new_sha256="abc123",
        )
        assert item.item_status == SyncItemStatus.UNCHANGED
        assert item.previous_sha256 == item.new_sha256

    def test_failed_item_has_error(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
            item_status=SyncItemStatus.FAILED,
            error_summary="Download timeout after 30s",
        )
        assert item.error_summary == "Download timeout after 30s"

    def test_http_fields_default_to_empty(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
        )
        assert item.http_etag == ""
        assert item.http_last_modified == ""
        assert item.http_status is None

    def test_item_with_http_headers(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
            item_status=SyncItemStatus.NEW,
            http_status=200,
            http_etag='"abc123"',
            http_last_modified="Mon, 01 Jan 2026 00:00:00 GMT",
            byte_size=150000,
        )
        assert item.http_status == 200
        assert item.http_etag == '"abc123"'
        assert item.byte_size == 150000

    def test_retry_count_defaults_to_zero(self):
        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=str(uuid.uuid4()),
            source_identifier="gii-bgb",
        )
        assert item.retry_count == 0


# ── SyncPlan Entity ─────────────────────────────


class TestSyncPlan:
    def test_create_empty_plan(self):
        plan = SyncPlan(
            sync_run_id=str(uuid.uuid4()),
            items=[],
            warnings=[],
            estimated_download_bytes=0,
        )
        assert len(plan.items) == 0
        assert len(plan.warnings) == 0

    def test_plan_with_items(self):
        items = [
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id="run-1",
                source_identifier="item-1",
                item_status=SyncItemStatus.NEW,
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id="run-1",
                source_identifier="item-2",
                item_status=SyncItemStatus.UNCHANGED,
            ),
        ]
        plan = SyncPlan(
            sync_run_id="run-1",
            items=items,
            warnings=["Source has not been synced before"],
            estimated_download_bytes=300000,
        )
        assert len(plan.items) == 2
        assert plan.items[0].item_status == SyncItemStatus.NEW
        assert plan.items[1].item_status == SyncItemStatus.UNCHANGED
        assert len(plan.warnings) == 1
        assert plan.estimated_download_bytes == 300000

    def test_plan_dry_run_flag(self):
        """SyncPlan with dry_run items indicates safe preview mode."""
        items = [
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id="run-1",
                source_identifier="item-1",
                item_status=SyncItemStatus.NEW,
            ),
        ]
        plan = SyncPlan(
            sync_run_id="run-1",
            items=items,
            warnings=[],
            estimated_download_bytes=0,
        )
        assert len(plan.items) == 1
        assert plan.items[0].item_status == SyncItemStatus.NEW

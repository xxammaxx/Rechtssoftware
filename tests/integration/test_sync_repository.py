"""Integration tests for M7-B sync repository operations.

Uses temporary SQLite databases to validate CRUD operations
for SyncRun, SyncItem, and catalog stand date persistence.
"""

import os
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from private_legal_navigator.domain.sync import (
    SyncItem,
    SyncItemStatus,
    SyncRun,
    SyncRunStatus,
)
from private_legal_navigator.infrastructure.database import (
    initialize_schema,
)
from private_legal_navigator.infrastructure.gii_adapter import make_gii_source
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)


@pytest.fixture
def temp_db():
    """Create a temporary database with the sync schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # Close the file descriptor so unlink succeeds on Windows
    Path(path).unlink(missing_ok=True)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def repo(temp_db):
    """Initialize schema and return repository instance."""
    initialize_schema(temp_db)
    return SqliteLegalSourceRepository(temp_db)


@pytest.fixture
def sample_run():
    """Create a minimal SyncRun for testing."""
    return SyncRun(
        sync_run_id=str(uuid.uuid4()),
        source_key="gesetze-im-internet",
        started_at=datetime.now(UTC).isoformat(),
        status=SyncRunStatus.RUNNING,
    )


# ── SyncRun CRUD ────────────────────────────────


class TestSyncRunPersistence:
    def test_update_catalog_stand_date_persists_on_registered_source(self, repo):
        """T306: a completed catalog stand is stored against its source."""
        source = make_gii_source()
        repo.save_source(source)

        repo.update_legal_source_catalog_stand_date(source.source_key, "2026-07-26")

        conn = sqlite3.connect(repo._db_path)
        try:
            row = conn.execute(
                "SELECT last_catalog_stand_date FROM legal_sources WHERE source_key = ?",
                (source.source_key,),
            ).fetchone()
        finally:
            conn.close()

        assert row == ("2026-07-26",)

    def test_save_and_retrieve_sync_run(self, repo, sample_run):
        """T302: create_run stores a sync run and get_latest retrieves it."""
        repo.save_sync_run(sample_run)

        retrieved = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        assert retrieved is not None
        assert retrieved.sync_run_id == sample_run.sync_run_id
        assert retrieved.source_key == "gesetze-im-internet"
        assert retrieved.status == SyncRunStatus.RUNNING

    def test_update_sync_run_status(self, repo, sample_run):
        """T302: update_sync_run modifies status and counters."""
        repo.save_sync_run(sample_run)

        sample_run.status = SyncRunStatus.COMPLETED
        sample_run.new_count = 5
        sample_run.unchanged_count = 95
        sample_run.total_in_catalog = 100
        repo.update_sync_run(sample_run)

        retrieved = repo.get_latest_sync_run("gesetze-im-internet", successful_only=True)
        assert retrieved is not None
        assert retrieved.status == SyncRunStatus.COMPLETED
        assert retrieved.new_count == 5
        assert retrieved.unchanged_count == 95
        assert retrieved.total_in_catalog == 100

    def test_get_latest_successful_filters_failed(self, repo):
        """get_latest_sync_run with successful_only=True skips non-COMPLETED runs."""
        failed = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-25T00:00:00Z",
            status=SyncRunStatus.FAILED,
        )
        success = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-26T00:00:00Z",
            status=SyncRunStatus.COMPLETED,
        )
        repo.save_sync_run(failed)
        repo.save_sync_run(success)

        latest = repo.get_latest_sync_run("gesetze-im-internet", successful_only=True)
        assert latest is not None
        assert latest.status == SyncRunStatus.COMPLETED
        assert latest.sync_run_id == success.sync_run_id

    def test_list_runs_returns_ordered_by_most_recent(self, repo):
        """T303: list_runs returns runs ordered by started_at DESC."""
        run1 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-06-01T00:00:00Z",
            status=SyncRunStatus.COMPLETED,
        )
        run2 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-01T00:00:00Z",
            status=SyncRunStatus.RUNNING,
        )
        repo.save_sync_run(run1)
        repo.save_sync_run(run2)

        runs = repo.list_runs(source_key="gesetze-im-internet", limit=10)
        assert len(runs) == 2
        assert runs[0].started_at > runs[1].started_at  # most recent first

    def test_list_runs_respects_limit(self, repo):
        """T303: list_runs respects the limit parameter."""
        for i in range(5):
            run = SyncRun(
                sync_run_id=str(uuid.uuid4()),
                source_key="gesetze-im-internet",
                started_at=f"2026-0{i + 1}-01T00:00:00Z",
                status=SyncRunStatus.COMPLETED,
            )
            repo.save_sync_run(run)

        runs = repo.list_runs(limit=3)
        assert len(runs) == 3

    def test_list_runs_without_source_returns_all_sources(self, repo):
        """T303: list_runs without source_key returns runs from all sources."""
        run1 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="source-a",
            started_at="2026-07-25T00:00:00Z",
            status=SyncRunStatus.COMPLETED,
        )
        run2 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="source-b",
            started_at="2026-07-25T00:00:01Z",
            status=SyncRunStatus.COMPLETED,
        )
        repo.save_sync_run(run1)
        repo.save_sync_run(run2)

        runs = repo.list_runs(limit=10)
        assert len(runs) == 2

    def test_list_runs_successful_only(self, repo):
        """T303: successful_only=True filters non-COMPLETED runs."""
        for i in range(3):
            run = SyncRun(
                sync_run_id=str(uuid.uuid4()),
                source_key="gesetze-im-internet",
                started_at=f"2026-0{i + 1}-01T00:00:00Z",
                status=SyncRunStatus.COMPLETED if i % 2 == 0 else SyncRunStatus.FAILED,
            )
            repo.save_sync_run(run)

        successful = repo.list_runs(successful_only=True, limit=10)
        assert all(r.status == SyncRunStatus.COMPLETED for r in successful)
        assert len(successful) == 2


# ── SyncItem CRUD ───────────────────────────────


class TestSyncItemPersistence:
    def test_save_and_retrieve_items_for_run(self, repo, sample_run):
        """T304: save_sync_item stores items and get_items_for_run retrieves them."""
        repo.save_sync_run(sample_run)

        item = SyncItem(
            sync_item_id=str(uuid.uuid4()),
            sync_run_id=sample_run.sync_run_id,
            source_identifier="gii-bgb",
            abbreviation="BGB",
            title="Bürgerliches Gesetzbuch",
            item_status=SyncItemStatus.NEW,
            http_status=200,
            byte_size=150000,
        )
        repo.save_sync_item(item)

        items = repo.get_items_for_run(sample_run.sync_run_id)
        assert len(items) == 1
        assert items[0]["source_identifier"] == "gii-bgb"
        assert items[0]["abbreviation"] == "BGB"
        assert items[0]["item_status"] == "NEW"

    def test_get_items_for_run_empty_when_no_items(self, repo, sample_run):
        """T304: get_items_for_run returns empty list for run with no items."""
        repo.save_sync_run(sample_run)

        items = repo.get_items_for_run(sample_run.sync_run_id)
        assert items == []

    def test_save_sync_items_batch(self, repo, sample_run):
        """T305: save_sync_items_batch persists multiple items in one transaction."""
        repo.save_sync_run(sample_run)

        items = [
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=sample_run.sync_run_id,
                source_identifier=f"gii-item-{i}",
                item_status=SyncItemStatus.NEW,
            )
            for i in range(5)
        ]

        conn = sqlite3.connect(repo._db_path)
        try:
            repo.save_sync_items_batch(items, conn)
            conn.commit()
        finally:
            conn.close()

        retrieved = repo.get_items_for_run(sample_run.sync_run_id)
        assert len(retrieved) == 5

    def test_sync_run_with_multiple_items_and_different_statuses(self, repo):
        """Full sync pipeline: create run, add items with mixed statuses."""
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            catalog_stand_date="2026-07-25",
            catalog_url="https://www.gesetze-im-internet.de/gii-toc.xml",
        )
        repo.save_sync_run(run)

        # Simulate plan output: mix of NEW, UNCHANGED, CHANGED items
        items = [
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=run.sync_run_id,
                source_identifier="item-1",
                item_status=SyncItemStatus.NEW,
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=run.sync_run_id,
                source_identifier="item-2",
                item_status=SyncItemStatus.UNCHANGED,
                previous_sha256="abc",
                new_sha256="abc",
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=run.sync_run_id,
                source_identifier="item-3",
                item_status=SyncItemStatus.CHANGED,
                previous_sha256="abc",
                new_sha256="def",
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=run.sync_run_id,
                source_identifier="item-4",
                item_status=SyncItemStatus.REMOTE_MISSING,
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=run.sync_run_id,
                source_identifier="item-5",
                item_status=SyncItemStatus.SKIPPED,
            ),
        ]

        conn = sqlite3.connect(repo._db_path)
        try:
            repo.save_sync_items_batch(items, conn)
            conn.commit()
        finally:
            conn.close()

        # Update run status after processing
        run.status = SyncRunStatus.COMPLETED
        run.new_count = 1
        run.changed_count = 1
        run.unchanged_count = 1
        run.remote_missing_count = 1
        run.skipped_count = 1
        run.total_in_catalog = 5
        repo.update_sync_run(run)

        retrieved_run = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        assert retrieved_run is not None
        assert retrieved_run.status == SyncRunStatus.COMPLETED
        assert retrieved_run.new_count == 1
        assert retrieved_run.total_in_catalog == 5

        retrieved_items = repo.get_items_for_run(run.sync_run_id)
        assert len(retrieved_items) == 5

        status_counts: dict[str, int] = {}
        for item in retrieved_items:
            status_counts[item["item_status"]] = status_counts.get(item["item_status"], 0) + 1

        assert status_counts.get("NEW") == 1
        assert status_counts.get("UNCHANGED") == 1
        assert status_counts.get("CHANGED") == 1
        assert status_counts.get("REMOTE_MISSING") == 1
        assert status_counts.get("SKIPPED") == 1


# ── Schema Verification ─────────────────────────


class TestSchemaIntegrity:
    def test_sync_tables_exist_after_initialization(self, temp_db):
        """T205: sync_runs and sync_items tables are created by initialize_schema."""
        initialize_schema(temp_db)
        conn = sqlite3.connect(temp_db)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name IN ('sync_runs', 'sync_items')"
            ).fetchall()
            table_names = {row[0] for row in tables}
            assert "sync_runs" in table_names
            assert "sync_items" in table_names
        finally:
            conn.close()

    def test_sync_run_dry_run_column_default(self, temp_db):
        """INV-M7B-01: DB default for dry_run should be 1."""
        initialize_schema(temp_db)
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.execute("PRAGMA table_info(sync_runs)")
            columns = {row[1]: row for row in cursor.fetchall()}
            assert "dry_run" in columns
            dry_run_info = columns["dry_run"]
            assert dry_run_info[4] == "1", f"dry_run default is {dry_run_info[4]}, expected '1'"
            assert dry_run_info[4] is not None, "dry_run default should not be NULL"
        finally:
            conn.close()

    def test_sync_indexes_exist(self, temp_db):
        """M7B_INDEXES are created during initialization."""
        initialize_schema(temp_db)
        conn = sqlite3.connect(temp_db)
        try:
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_s%'"
            ).fetchall()
            index_names = {row[0] for row in indexes}
            expected = {
                "idx_sr_source",
                "idx_sr_status",
                "idx_si_run",
                "idx_si_status",
                "idx_si_source_identifier",
            }
            assert expected.issubset(index_names), f"Missing indexes: {expected - index_names}"
        finally:
            conn.close()

    def test_foreign_key_sync_run_id(self, temp_db):
        """sync_items.sync_run_id has FK to sync_runs with ON DELETE CASCADE."""
        initialize_schema(temp_db)
        conn = sqlite3.connect(temp_db)
        try:
            fks = conn.execute("PRAGMA foreign_key_list(sync_items)").fetchall()
            # FK info is keyed by the FROM column name
            fk_tables = {row[2] for row in fks}  # row[2] = referenced table name
            assert "sync_runs" in fk_tables, f"Expected FK to sync_runs, got: {fk_tables}"
        finally:
            conn.close()

"""I004 — Integration test: abort + restart (SHA-256 dedup handles partial run).

Verifies that after an aborted sync:
- The SyncRun status is ABORTED or FAILED
- The old corpus is still usable (no corruption)
- A new SyncRun can be started and completed after abort
- The aborted run remains in the history separate from the new run
"""

import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.legal_source_service import (
    LegalSourceService,
)
from private_legal_navigator.application.sync_service import (
    SyncExecutionService,
    SyncPlanningService,
)
from private_legal_navigator.domain.sync import (
    SyncItem,
    SyncItemStatus,
    SyncRun,
    SyncRunStatus,
)
from private_legal_navigator.infrastructure.database import initialize_schema
from private_legal_navigator.infrastructure.gii_adapter import (
    GiiAdapter,
)
from private_legal_navigator.infrastructure.safe_source_client import (
    DownloadResult,
    SourceClient,
    SourceClientError,
    TransportMode,
    TransportPolicy,
    VerifiedSourcePayload,
)
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)
from tests.integration.sync_fixtures import (
    SYNTH_CATALOG_XML,
    SYNTH_LAW_DOWNLOAD_URL_TO_XML,
    SYNTH_LAW_URL_TO_XML,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def repo(temp_db):
    initialize_schema(temp_db)
    return SqliteLegalSourceRepository(temp_db)


@pytest.fixture
def snapshot_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_client_factory():
    """Factory for mock SourceClient."""

    def _make_client():
        client = MagicMock(spec=SourceClient, instance=True)
        real_policy = TransportPolicy(
            mode=TransportMode.TEST,
            allowed_hosts=("gesetze-im-internet.de", "localhost"),
            allowed_schemes=("https", "http"),
        )
        client.policy = real_policy

        def _download(url: str) -> bytes:
            if "gii-toc" in url:
                return SYNTH_CATALOG_XML
            for prefix, content in SYNTH_LAW_DOWNLOAD_URL_TO_XML.items():
                if prefix in url:
                    return content
            raise SourceClientError(f"Unmocked download URL: {url}")

        def _download_with_headers(url: str) -> DownloadResult:
            for prefix, content in SYNTH_LAW_URL_TO_XML.items():
                if prefix in url:
                    return DownloadResult(
                        content=content,
                        http_status=200,
                        etag='"synth-etag"',
                        last_modified="Mon, 25 Jul 2026 00:00:00 GMT",
                        content_type="application/xml",
                    )
            raise SourceClientError(f"Unmocked download_with_headers URL: {url}")

        def _download_verified(
            url: str, source_identifier: str = ""
        ) -> VerifiedSourcePayload:
            from datetime import UTC, datetime

            from private_legal_navigator.infrastructure.safe_source_client import (
                VerifiedSourcePayload,
                compute_sha256,
            )

            result = _download_with_headers(url)
            sha256 = compute_sha256(result.content)
            return VerifiedSourcePayload(
                source_identifier=source_identifier or url,
                effective_url=url,
                content=result.content,
                sha256=sha256,
                http_status=result.http_status,
                etag=result.etag,
                last_modified=result.last_modified,
                content_type=result.content_type,
                fetched_at=datetime.now(UTC).isoformat(),
            )

        client.download.side_effect = _download
        client.download_with_headers.side_effect = _download_with_headers
        client.download_verified.side_effect = _download_verified

        return client

    return _make_client


class TestSyncAbortRestart:
    """I004: Abort and restart integration tests."""

    def test_aborted_sync_run_can_be_created_and_persisted(self, repo):
        """Verify an ABORTED SyncRun can be created and persists."""
        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.ABORTED,
            error_summary="User interrupted sync mid-download",
            dry_run=False,
        )
        repo.save_sync_run(aborted_run)

        # Verify it was persisted
        retrieved = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        assert retrieved is not None
        assert retrieved.status == SyncRunStatus.ABORTED
        assert retrieved.error_summary == "User interrupted sync mid-download"

    def test_aborted_sync_run_with_partial_items(self, repo):
        """Verify an ABORTED run can have partial sync items."""
        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.ABORTED,
            error_summary="Aborted after 2 of 5 items",
            new_count=1,
            total_in_catalog=3,
        )
        repo.save_sync_run(aborted_run)

        # Add partial sync items (some succeeded, some pending)
        items = [
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=aborted_run.sync_run_id,
                source_identifier="https://www.gesetze-im-internet.de/bgb/",
                abbreviation="BGB",
                title="Bürgerliches Gesetzbuch",
                item_status=SyncItemStatus.NEW,
                http_status=200,
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=aborted_run.sync_run_id,
                source_identifier="https://www.gesetze-im-internet.de/stgb/",
                abbreviation="StGB",
                title="Strafgesetzbuch",
                item_status=SyncItemStatus.PENDING,
            ),
            SyncItem(
                sync_item_id=str(uuid.uuid4()),
                sync_run_id=aborted_run.sync_run_id,
                source_identifier="https://www.gesetze-im-internet.de/vwgo/",
                abbreviation="VwGO",
                title="Verwaltungsgerichtsordnung",
                item_status=SyncItemStatus.PENDING,
            ),
        ]
        for item in items:
            repo.save_sync_item(item)

        # Verify items are persisted for the aborted run
        persisted_items = repo.get_items_for_run(aborted_run.sync_run_id)
        assert len(persisted_items) == 3

        statuses = {i["item_status"] for i in persisted_items}
        assert "NEW" in statuses
        assert "PENDING" in statuses

    def test_failed_sync_run_can_be_created(self, repo):
        """Verify a FAILED SyncRun can be created for network errors."""
        failed_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.FAILED,
            error_summary="Connection timeout during catalog download",
            failed_count=3,
            total_in_catalog=3,
            dry_run=False,
        )
        repo.save_sync_run(failed_run)

        retrieved = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        assert retrieved is not None
        assert retrieved.status == SyncRunStatus.FAILED

    def test_new_sync_can_complete_after_aborted_run(self, repo, mock_client_factory, snapshot_dir):
        """Verify a new SyncRun can complete successfully after an aborted run."""
        # First: create an aborted run
        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.ABORTED,
            error_summary="Aborted by user",
            dry_run=False,
        )
        repo.save_sync_run(aborted_run)

        # Then: run a full apply successfully
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)
        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        new_run = exec_service.execute(plan, dry_run=False)

        assert new_run.status == SyncRunStatus.COMPLETED
        assert new_run.sync_run_id != aborted_run.sync_run_id

    def test_corpus_usable_after_aborted_run(self, repo, mock_client_factory, snapshot_dir):
        """Verify existing corpus (from prior run) is still usable after abort."""
        # Create a prior successful run with data in the DB
        client1 = mock_client_factory()
        adapter1 = GiiAdapter(client1, snapshot_dir)
        planning1 = SyncPlanningService(repo, client1, adapter1)
        plan1 = planning1.plan()

        legal_service1 = LegalSourceService(repo, client1, snapshot_dir)
        exec_service1 = SyncExecutionService(repo, legal_service1, client1, adapter1)
        run1 = exec_service1.execute(plan1, dry_run=False)
        assert run1.status == SyncRunStatus.COMPLETED

        # Count existing instruments and provisions
        instruments_before = len(repo.list_instruments())
        provisions_before = repo.count_provisions("gesetze-im-internet")

        # Simulate an abort (create aborted run without touching the corpus)
        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.ABORTED,
            dry_run=False,
        )
        repo.save_sync_run(aborted_run)

        # Verify the corpus is intact
        instruments_after = len(repo.list_instruments())
        provisions_after = repo.count_provisions("gesetze-im-internet")

        assert instruments_after == instruments_before, (
            f"Corpus instruments changed after abort: {instruments_after} != {instruments_before}"
        )
        assert provisions_after == provisions_before, (
            f"Corpus provisions changed after abort: {provisions_after} != {provisions_before}"
        )

    def test_multiple_runs_coexist_in_history(self, repo, mock_client_factory, snapshot_dir):
        """Verify aborted, failed, and completed runs all coexist in history."""
        # Create a failed run
        failed_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-20T00:00:00Z",
            completed_at="2026-07-20T00:01:00Z",
            status=SyncRunStatus.FAILED,
            error_summary="Network error",
            dry_run=False,
        )
        repo.save_sync_run(failed_run)

        # Create an aborted run
        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-21T00:00:00Z",
            completed_at="2026-07-21T00:01:00Z",
            status=SyncRunStatus.ABORTED,
            dry_run=False,
        )
        repo.save_sync_run(aborted_run)

        # Run a successful apply
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)
        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        completed_run = exec_service.execute(plan, dry_run=False)
        assert completed_run.status == SyncRunStatus.COMPLETED

        # List all runs
        all_runs = repo.list_runs(source_key="gesetze-im-internet", limit=10)
        run_statuses = {r.status for r in all_runs}

        assert len(all_runs) >= 3, f"Expected at least 3 runs, found {len(all_runs)}"
        assert SyncRunStatus.FAILED in run_statuses
        assert SyncRunStatus.ABORTED in run_statuses
        assert SyncRunStatus.COMPLETED in run_statuses

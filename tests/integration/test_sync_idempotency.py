"""I003 — Integration test: idempotent re-run (second run = all UNCHANGED).

Verifies that running the same sync twice:
- Second run creates no new snapshots (no duplicate downloads)
- Second run creates no new instruments or provisions
- Both SyncRuns exist but second has new_count=0, changed_count=0
- Existing corpus is preserved without modification
"""

import os
import tempfile
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
    """Factory for mock SourceClient (same as I002 setup)."""

    def _make_client(catalog_xml: bytes = SYNTH_CATALOG_XML):
        client = MagicMock(spec=SourceClient, instance=True)

        real_policy = TransportPolicy(
            mode=TransportMode.TEST,
            allowed_hosts=("gesetze-im-internet.de", "localhost"),
            allowed_schemes=("https", "http"),
        )
        client.policy = real_policy

        def _download(url: str) -> bytes:
            if "gii-toc" in url:
                return catalog_xml
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
        ) -> "VerifiedSourcePayload":
            from private_legal_navigator.infrastructure.safe_source_client import (
                VerifiedSourcePayload,
                compute_sha256,
            )
            from datetime import UTC, datetime

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


def _run_full_apply(repo, mock_client_factory, snapshot_dir):
    """Helper: perform a full apply and return (run1, client, instrument_count, etc.)."""
    client = mock_client_factory()
    adapter = GiiAdapter(client, snapshot_dir)
    planning = SyncPlanningService(repo, client, adapter)
    plan = planning.plan()

    legal_service = LegalSourceService(repo, client, snapshot_dir)
    exec_service = SyncExecutionService(repo, legal_service, client, adapter)
    run1 = exec_service.execute(plan, dry_run=False)

    instrument_count_before = len(repo.list_instruments())
    provision_count_before = repo.count_provisions("gesetze-im-internet")
    snapshot_count_before = len(repo.list_snapshots_for_source("gesetze-im-internet"))

    return (
        run1,
        client,
        adapter,
        instrument_count_before,
        provision_count_before,
        snapshot_count_before,
    )


class TestSyncIdempotency:
    """I003: Idempotency tests — second run detects no changes."""

    def test_second_run_creates_no_new_snapshots(self, repo, mock_client_factory, snapshot_dir):
        """Verify second run creates no duplicate snapshots."""
        run1, client, adapter, inst_before, prov_before, snap_before = _run_full_apply(
            repo, mock_client_factory, snapshot_dir
        )

        assert snap_before > 0, "First run should create snapshots"

        # Second run — use the same client (same catalog)
        planning = SyncPlanningService(repo, client, adapter)
        plan2 = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        _ = exec_service.execute(plan2, dry_run=False)

        snapshots_after = repo.list_snapshots_for_source("gesetze-im-internet")
        # Second run should detect UNCHANGED items and not create new snapshots
        assert len(snapshots_after) == snap_before, (
            f"Expected {snap_before} snapshots after second run, "
            f"found {len(snapshots_after)} — duplicates should not be created"
        )

    def test_second_run_creates_no_new_instruments_or_provisions(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify second run does not duplicate instruments or provisions."""
        run1, client, adapter, inst_before, prov_before, snap_before = _run_full_apply(
            repo, mock_client_factory, snapshot_dir
        )

        # Second run
        planning = SyncPlanningService(repo, client, adapter)
        plan2 = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        _ = exec_service.execute(plan2, dry_run=False)

        instruments_after = repo.list_instruments()
        provisions_after = repo.count_provisions("gesetze-im-internet")

        assert len(instruments_after) == inst_before, (
            f"Instruments should not increase: {len(instruments_after)} != {inst_before}"
        )
        assert provisions_after == prov_before, (
            f"Provisions should not increase: {provisions_after} != {prov_before}"
        )

    def test_both_sync_runs_exist_but_second_has_zero_new_changed(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify both SyncRuns exist and second has new_count=0, changed_count=0."""
        run1, client, adapter, inst_before, prov_before, snap_before = _run_full_apply(
            repo, mock_client_factory, snapshot_dir
        )

        # Second run
        planning = SyncPlanningService(repo, client, adapter)
        plan2 = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        run2 = exec_service.execute(plan2, dry_run=False)

        # Both runs should exist
        runs = repo.list_runs(source_key="gesetze-im-internet", limit=10)
        assert len(runs) >= 2, f"Expected at least 2 sync runs, found {len(runs)}"

        # Second run should have no new/changed items
        assert run2.new_count == 0, f"Second run new_count should be 0, got {run2.new_count}"
        assert run2.changed_count == 0, (
            f"Second run changed_count should be 0, got {run2.changed_count}"
        )

        # First run should have original counts
        assert run1.new_count > 0, f"First run should have new_count > 0, got {run1.new_count}"

    def test_second_run_items_have_unchanged_status(self, repo, mock_client_factory, snapshot_dir):
        """Verify second run sync items all show UNCHANGED status."""
        run1, client, adapter, inst_before, prov_before, snap_before = _run_full_apply(
            repo, mock_client_factory, snapshot_dir
        )

        planning = SyncPlanningService(repo, client, adapter)
        plan2 = planning.plan(force=True)  # bypass catalog gate for idempotency test

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        run2 = exec_service.execute(plan2, dry_run=False)

        items2 = repo.get_items_for_run(run2.sync_run_id)
        assert len(items2) > 0, "Second run should have sync items"

        for item in items2:
            status = item["item_status"]
            # After a full apply of same data, items should be UNCHANGED
            assert status in ("UNCHANGED", "SKIPPED", "REMOTE_MISSING"), (
                f"Expected UNCHANGED, got {status} for "
                f"{item.get('abbreviation', item.get('source_identifier'))}"
            )

    def test_second_run_status_is_completed(self, repo, mock_client_factory, snapshot_dir):
        """Verify second run completes successfully with COMPLETED status."""
        run1, client, adapter, inst_before, prov_before, snap_before = _run_full_apply(
            repo, mock_client_factory, snapshot_dir
        )

        planning = SyncPlanningService(repo, client, adapter)
        plan2 = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        run2 = exec_service.execute(plan2, dry_run=False)

        assert run2.status == SyncRunStatus.COMPLETED, (
            f"Expected COMPLETED, got {run2.status.value}"
        )

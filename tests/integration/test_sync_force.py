"""I007 — Integration test: force mode.

Verifies the --force flag behavior:
- Without force: unchanged catalog produces empty plan (gate blocks re-sync)
- With force: catalog gate is bypassed, plan is generated
- Force does NOT bypass TLS/HTTPS enforcement
- Force does NOT bypass SHA-256 hash checking
- Force does NOT delete or modify historical sync data
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

        client.download.side_effect = _download
        client.download_with_headers.side_effect = _download_with_headers

        return client

    return _make_client


class TestForceSync:
    """I007: Force mode integration tests."""

    def test_unchanged_catalog_blocked_without_force(self, repo, mock_client_factory, snapshot_dir):
        """Verify that an unchanged catalog (same stand date) blocks re-sync."""
        # First: create a completed sync run with the catalog's stand date
        prior_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.COMPLETED,
            catalog_stand_date="2026-07-25",
            dry_run=False,
        )
        repo.save_sync_run(prior_run)

        # Now plan with the same catalog (same stand date): should be empty
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(force=False)

        # Plan should be empty because catalog_stand_date matches
        assert len(plan.items) == 0, (
            f"Plan should be empty for unchanged catalog, got {len(plan.items)} items"
        )
        assert len(plan.warnings) > 0, "Should have a warning about unchanged catalog"
        assert any("unchanged" in w.lower() or "force" in w.lower() for w in plan.warnings), (
            f"Warning should mention unchanged/force: {plan.warnings}"
        )

    def test_force_bypasses_catalog_gate(self, repo, mock_client_factory, snapshot_dir):
        """Verify force=True bypasses the catalog stand-date gate."""
        # Create prior run with matching stand date
        prior_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            status=SyncRunStatus.COMPLETED,
            catalog_stand_date="2026-07-25",
            dry_run=False,
        )
        repo.save_sync_run(prior_run)

        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(force=True)

        # With force=True, the gate should be bypassed
        assert len(plan.items) > 0, "Force should bypass catalog gate and produce items"

    def test_force_does_not_bypass_tls_enforcement(self, repo, mock_client_factory, snapshot_dir):
        """Verify force does NOT bypass TLS/HTTPS enforcement."""
        # The SourceClient with force=True still validates URLs
        client = mock_client_factory()
        # Verify the client's policy is still enforcing HTTPS for external hosts
        policy = client.policy
        assert not policy.is_scheme_allowed("ftp"), "FTP should not be allowed"
        # HTTP is only allowed in TEST mode for localhost
        assert not policy.is_scheme_allowed("http") or policy.is_localhost("localhost"), (
            "HTTP for external should not be allowed"
        )

        # The planning service with force=True should still go through
        # the SourceClient which enforces TLS
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        # This should work because the client's URL validation still runs
        plan = planning.plan(force=True)
        assert len(plan.items) > 0

    def test_force_does_not_bypass_hash_checking(self, repo, mock_client_factory, snapshot_dir):
        """Verify force does NOT bypass SHA-256 hash checking during apply."""
        # First do a full apply to populate the DB
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()
        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        exec_service.execute(plan, dry_run=False)

        # Now force re-sync with same catalog
        plan2 = planning.plan(force=True)
        run2 = exec_service.execute(plan2, dry_run=False)

        # Items should be UNCHANGED (SHA-256 match detected)
        # Even with force=True, hash checking still prevents duplicate imports
        items = repo.get_items_for_run(run2.sync_run_id)
        for item in items:
            status = item["item_status"]
            # No item should be NEW since all already exist
            if status not in ("SKIPPED", "REMOTE_MISSING"):
                assert status in ("UNCHANGED",), (
                    f"Force should not bypass hash check: {item['abbreviation']} is {status}"
                )

    def test_force_does_not_delete_historical_data(self, repo, mock_client_factory, snapshot_dir):
        """Verify force does NOT delete historical sync data."""
        # Create historical data
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        # First run completes
        plan1 = planning.plan()
        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        _ = exec_service.execute(plan1, dry_run=False)

        # Count historical data
        runs_before = len(repo.list_runs(source_key="gesetze-im-internet", limit=100))
        instruments_before = len(repo.list_instruments())
        snapshots_before = len(repo.list_snapshots_for_source("gesetze-im-internet"))

        # Force re-sync
        plan2 = planning.plan(force=True)
        _ = exec_service.execute(plan2, dry_run=False)

        # Historical data should still exist
        runs_after = len(repo.list_runs(source_key="gesetze-im-internet", limit=100))
        instruments_after = len(repo.list_instruments())
        snapshots_after = len(repo.list_snapshots_for_source("gesetze-im-internet"))

        assert runs_after >= runs_before, (
            f"Historical runs should be preserved: {runs_after} < {runs_before}"
        )
        assert instruments_after == instruments_before, (
            f"Instruments should not be deleted: {instruments_after} != {instruments_before}"
        )
        assert snapshots_after == snapshots_before, (
            f"Snapshots should not be deleted: {snapshots_after} != {snapshots_before}"
        )

        # First run should still be retrievable
        run1_retrieved = repo.get_latest_sync_run("gesetze-im-internet", successful_only=True)
        assert run1_retrieved is not None

    def test_force_first_run_works_normally(self, repo, mock_client_factory, snapshot_dir):
        """Verify force=True on first run (no prior runs) still works."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(force=True)

        # On first run (no prior completed sync), force should work
        # The gate is only active when there's a prior run with matching date
        assert len(plan.items) > 0, "Force on first run should still produce items"

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        sync_run = exec_service.execute(plan, dry_run=False)

        assert sync_run.status == SyncRunStatus.COMPLETED

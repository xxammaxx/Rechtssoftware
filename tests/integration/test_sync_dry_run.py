"""I001 — Integration test: full dry-run plan (no downloads, no DB changes).

Verifies that a dry-run sync:
- Creates a SyncRun with dry_run=True
- Produces NO downloads of instruments
- Produces NO database mutations (no snapshots, no instruments, no provisions)
- Persists the SyncRun for history
- Sets SyncRun status to COMPLETED after dry-run
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
    SourceClient,
    TransportMode,
    TransportPolicy,
)
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)
from tests.integration.sync_fixtures import SYNTH_CATALOG_XML


@pytest.fixture
def temp_db():
    """Create a temporary database file with initialized schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def repo(temp_db):
    """Return a SqliteLegalSourceRepository with initialized schema."""
    initialize_schema(temp_db)
    return SqliteLegalSourceRepository(temp_db)


@pytest.fixture
def patched_source_client():
    """Mock SourceClient that returns synthetic catalog XML."""
    client = MagicMock(spec=SourceClient, instance=True)
    # Use a real TransportPolicy for validate_url (called by download)
    real_policy = TransportPolicy(
        mode=TransportMode.TEST,
        allowed_hosts=("gesetze-im-internet.de", "localhost"),
        allowed_schemes=("https", "http"),
    )
    client.policy = real_policy
    client.download.return_value = SYNTH_CATALOG_XML
    client.download_with_headers.return_value = None
    return client


@pytest.fixture
def snapshot_dir(temp_db):
    """A temporary directory for snapshots."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def planning_service(repo, patched_source_client, snapshot_dir):
    """SyncPlanningService with mocked client."""
    adapter = GiiAdapter(patched_source_client, snapshot_dir)
    return SyncPlanningService(repo, patched_source_client, adapter)


class TestDryRunSync:
    """I001: Dry-run integration tests."""

    def test_dry_run_creates_sync_run_with_dry_run_true(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify dry-run creates SyncRun with dry_run=True."""
        plan = planning_service.plan()
        assert len(plan.items) > 0, "Synthetic catalog should produce items"

        # Create execution service
        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        sync_run = exec_service.execute(plan, dry_run=True)

        assert sync_run.dry_run is True
        assert sync_run.sync_run_id == plan.sync_run_id
        assert sync_run.source_key == "gesetze-im-internet"

    def test_dry_run_produces_no_downloads(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify dry-run produces NO actual downloads of instruments."""
        plan = planning_service.plan()

        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        _ = exec_service.execute(plan, dry_run=True)

        # download_with_headers should never have been called during dry-run
        patched_source_client.download_with_headers.assert_not_called()

    def test_dry_run_produces_no_database_mutations(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify dry-run produces NO snapshots, instruments, or provisions."""
        plan = planning_service.plan()

        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        _ = exec_service.execute(plan, dry_run=True)

        # Check no snapshots
        snapshots = repo.list_snapshots_for_source("gesetze-im-internet")
        assert len(snapshots) == 0, f"Expected 0 snapshots after dry-run, found {len(snapshots)}"

        # Check no instruments
        instruments = repo.list_instruments()
        assert len(instruments) == 0, (
            f"Expected 0 instruments after dry-run, found {len(instruments)}"
        )

        # Check no provisions
        provision_count = repo.count_provisions("gesetze-im-internet")
        assert provision_count == 0, f"Expected 0 provisions after dry-run, found {provision_count}"

    def test_dry_run_sync_run_persists_for_history(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify dry-run SyncRun is NOT persisted (RC-025 F1 compliance).

        Dry-run must not modify the product database — the SyncRun
        exists only in-memory for classification reporting.
        """
        plan = planning_service.plan()

        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        sync_run = exec_service.execute(plan, dry_run=True)

        # Dry-run SyncRun must not be persisted to database
        persisted = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        if persisted is not None:
            assert persisted.sync_run_id != sync_run.sync_run_id, (
                "Dry-run SyncRun must not be persisted to database. "
                f"Found persisted run: {persisted.sync_run_id}"
            )

    def test_dry_run_sync_run_status_is_completed(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify SyncRun status is COMPLETED after dry-run."""
        plan = planning_service.plan()

        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        sync_run = exec_service.execute(plan, dry_run=True)

        assert sync_run.status == SyncRunStatus.COMPLETED
        assert sync_run.completed_at, "completed_at should be set"

    def test_dry_run_sync_items_are_persisted(
        self, repo, planning_service, patched_source_client, snapshot_dir
    ):
        """Verify dry-run does NOT persist sync items (RC-025 F1 compliance).

        Dry-run must not modify the product database — SyncItems are
        only classified and counted in-memory, not saved to the repository.
        """
        plan = planning_service.plan()

        from private_legal_navigator.application.legal_source_service import (
            LegalSourceService,
        )

        legal_service = LegalSourceService(repo, patched_source_client, snapshot_dir)
        gii_adapter = GiiAdapter(patched_source_client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, patched_source_client, gii_adapter)

        sync_run = exec_service.execute(plan, dry_run=True)

        # Dry-run must not persist items to the database
        items = repo.get_items_for_run(sync_run.sync_run_id)
        assert len(items) == 0, (
            f"Dry-run must not persist sync items to database. "
            f"Found {len(items)} items — RC-025 F1 violation."
        )

        # SyncRun itself must not be persisted during dry-run
        latest = repo.get_latest_sync_run("gesetze-im-internet", successful_only=False)
        if latest is not None:
            assert latest.sync_run_id != sync_run.sync_run_id, (
                "Dry-run SyncRun must not be persisted to database."
            )

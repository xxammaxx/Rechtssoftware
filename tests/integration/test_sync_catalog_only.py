"""I006 — Integration test: catalog-only mode.

Verifies that in catalog-only mode:
- Catalog is fetched (planning phase runs)
- SyncPlan is generated with classified items
- No database mutations occur (no snapshots, instruments, provisions)
- No sync runs are persisted (since we don't execute)
- The plan correctly classifies all catalog items
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.sync_service import (
    SyncPlanningService,
)
from private_legal_navigator.domain.sync import (
    SyncItemStatus,
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
def planning_service(repo, snapshot_dir):
    """Create SyncPlanningService with mocked SourceClient (catalog-only)."""
    client = MagicMock(spec=SourceClient, instance=True)
    real_policy = TransportPolicy(
        mode=TransportMode.TEST,
        allowed_hosts=("gesetze-im-internet.de", "localhost"),
        allowed_schemes=("https", "http"),
    )
    client.policy = real_policy
    client.download.return_value = SYNTH_CATALOG_XML

    adapter = GiiAdapter(client, snapshot_dir)
    return SyncPlanningService(repo, client, adapter)


class TestCatalogOnlySync:
    """I006: Catalog-only sync tests (planning without execution)."""

    def test_catalog_only_generates_plan_without_database_mutations(
        self, repo, planning_service, snapshot_dir
    ):
        """Verify planning generates a SyncPlan but makes no DB changes."""
        # Before planning: no data in DB
        instruments_before = len(repo.list_instruments())
        snapshots_before = len(repo.list_snapshots_for_source("gesetze-im-internet"))
        runs_before = len(repo.list_runs(limit=100))

        # Run planning only (no execution)
        plan = planning_service.plan()

        # After planning: still no data in DB
        instruments_after = len(repo.list_instruments())
        snapshots_after = len(repo.list_snapshots_for_source("gesetze-im-internet"))
        runs_after = len(repo.list_runs(limit=100))

        assert instruments_after == instruments_before == 0, (
            f"Planning should not create instruments: {instruments_after}"
        )
        assert snapshots_after == snapshots_before == 0, (
            f"Planning should not create snapshots: {snapshots_after}"
        )
        assert runs_after == runs_before == 0, f"Planning should not create sync runs: {runs_after}"

        # But the plan should contain items
        assert len(plan.items) > 0, "Plan should have classified items"
        assert plan.sync_run_id, "Plan should have a sync_run_id"

    def test_catalog_only_classifies_items_correctly_for_empty_repo(
        self, repo, planning_service, snapshot_dir
    ):
        """Verify all items are classified as NEW when repo is empty."""
        plan = planning_service.plan()

        for item in plan.items:
            assert item.item_status == SyncItemStatus.NEW, (
                f"All items should be NEW in empty DB, "
                f"but {item.abbreviation} is {item.item_status.value}"
            )

        # There should be 3 items from our synthetic catalog
        assert len(plan.items) == 3, f"Expected 3 items, got {len(plan.items)}"

    def test_catalog_only_plan_has_estimated_download_size(
        self, repo, planning_service, snapshot_dir
    ):
        """Verify the plan includes an estimated download byte count."""
        plan = planning_service.plan()

        # Download estimate should be non-zero when there are NEW items
        assert plan.estimated_download_bytes > 0, (
            f"Expected positive download estimate, got {plan.estimated_download_bytes}"
        )

    def test_catalog_only_plan_has_sync_run_id(self, repo, planning_service, snapshot_dir):
        """Verify the plan generates a UUID for the sync run."""
        plan = planning_service.plan()

        assert plan.sync_run_id, "Plan should have a sync_run_id"
        # Verify it's a valid UUID
        try:
            uuid.UUID(plan.sync_run_id)
        except ValueError:
            pytest.fail(f"sync_run_id '{plan.sync_run_id}' is not a valid UUID")

    def test_catalog_only_no_sync_runs_persisted(self, repo, planning_service, snapshot_dir):
        """Verify that planning alone never creates sync run records."""
        plan = planning_service.plan()

        # The sync_run_id exists in the plan but should NOT be in the DB
        runs = repo.list_runs(limit=100)
        plan_ids = {r.sync_run_id for r in runs}
        assert plan.sync_run_id not in plan_ids, (
            f"Plan sync_run_id should not be in DB: {plan.sync_run_id}"
        )

        # No runs should exist at all
        assert len(runs) == 0, f"Expected 0 runs, found {len(runs)}"

    def test_catalog_only_empty_catalog_plan(self, repo, snapshot_dir):
        """Verify an empty catalog produces an empty plan with a warning."""
        empty_catalog = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n<gii-toc stand="2026-07-25">\n</gii-toc>\n'
        )

        client = MagicMock(spec=SourceClient, instance=True)
        real_policy = TransportPolicy(
            mode=TransportMode.TEST,
            allowed_hosts=("gesetze-im-internet.de",),
            allowed_schemes=("https",),
        )
        client.policy = real_policy
        client.download.return_value = empty_catalog

        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        assert len(plan.items) == 0, "Empty catalog should produce empty plan"
        assert len(plan.warnings) > 0, "Should warn about empty catalog"
        assert "empty" in plan.warnings[0].lower(), (
            f"Warning should mention 'empty': {plan.warnings}"
        )

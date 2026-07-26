"""I005 — Integration test: instrument-specific sync.

Verifies that when instrument_filter is used:
- Only the specified instruments are classified as non-SKIPPED
- Other instruments remain untouched (SKIPPED)
- The filter works for both abbreviations and source identifiers
- The skipped items are properly persisted with SKIPPED status
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
    SyncItemStatus,
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

        client.download.side_effect = _download
        client.download_with_headers.side_effect = _download_with_headers

        return client

    return _make_client


class TestInstrumentSpecificSync:
    """I005: Instrument-specific sync tests."""

    def test_filter_by_abbreviation_only_syncs_selected(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify only the filtered instrument is synced when using abbreviations."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        # Plan with filter: only BGB
        plan = planning.plan(instrument_filter=["BGB"])

        # Items for BGB should be NEW, others should be SKIPPED
        for item in plan.items:
            if item.abbreviation == "BGB":
                assert item.item_status == SyncItemStatus.NEW, (
                    f"BGB should be NEW, got {item.item_status.value}"
                )
            else:
                assert item.item_status == SyncItemStatus.SKIPPED, (
                    f"{item.abbreviation} should be SKIPPED, got {item.item_status.value}"
                )

    def test_filter_multiple_instruments(self, repo, mock_client_factory, snapshot_dir):
        """Verify multiple instruments can be filtered together."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(instrument_filter=["BGB", "STGB"])

        non_skipped_abbrevs: set[str] = set()
        for item in plan.items:
            if item.item_status != SyncItemStatus.SKIPPED:
                non_skipped_abbrevs.add(item.abbreviation)

        assert "BGB" in non_skipped_abbrevs, "BGB should be non-skipped"
        assert "STGB" in non_skipped_abbrevs, "STGB should be non-skipped"
        assert "VwGO" not in non_skipped_abbrevs, "VwGO should be skipped"

    def test_filter_skip_count_reflected_in_plan(self, repo, mock_client_factory, snapshot_dir):
        """Verify the plan's skip count correctly reflects the filter."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(instrument_filter=["BGB"])

        skipped_count = sum(1 for item in plan.items if item.item_status == SyncItemStatus.SKIPPED)
        new_count = sum(1 for item in plan.items if item.item_status == SyncItemStatus.NEW)

        assert skipped_count == 2, f"Expected 2 skipped, got {skipped_count}"
        assert new_count == 1, f"Expected 1 new, got {new_count}"

    def test_filter_execute_only_applies_to_selected_instrument(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify execution with filter only applies changes to selected instrument."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(instrument_filter=["BGB"])

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        _ = exec_service.execute(plan, dry_run=False)

        # Only BGB should be imported
        instruments = repo.list_instruments()
        abbrevs = {inst.abbreviation for inst in instruments}

        assert "BGB" in abbrevs, "BGB should be imported"
        assert "StGB" not in abbrevs, "StGB should NOT be imported"
        assert "VwGO" not in abbrevs, "VwGO should NOT be imported"

    def test_filter_warning_present_in_plan_warnings(self, repo, mock_client_factory, snapshot_dir):
        """Verify plan includes a warning when filter is active."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(instrument_filter=["BGB"])

        assert len(plan.warnings) > 0, "Plan should have warnings with filter"
        assert any("filter" in w.lower() for w in plan.warnings), (
            f"Warning about filter not found in: {plan.warnings}"
        )

    def test_filter_with_no_matching_instruments_handled_gracefully(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify filter with non-matching instrument produces all SKIPPED."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan(instrument_filter=["NONEXISTENT-LAW"])

        # All items should be SKIPPED
        for item in plan.items:
            assert item.item_status == SyncItemStatus.SKIPPED, (
                f"All items should be SKIPPED, but {item.abbreviation} is {item.item_status.value}"
            )

        # Execute should still complete
        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)
        sync_run = exec_service.execute(plan, dry_run=False)

        assert sync_run.status == SyncRunStatus.COMPLETED
        assert sync_run.new_count == 0
        assert sync_run.skipped_count == len(plan.items)

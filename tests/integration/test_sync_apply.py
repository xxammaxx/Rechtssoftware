"""I002 — Integration test: full apply run (with synthetic catalog and law XML).

Verifies that an apply sync:
- Creates a SyncRun with dry_run=False
- Actually downloads and imports instruments
- Creates sync_items with appropriate statuses
- Produces correct SyncRun summary counts
- Persists snapshots, instruments, and provisions in the database
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
def snapshot_dir():
    """A temporary directory for snapshots."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_client_factory():
    """Returns a factory for creating properly configured mock SourceClients."""

    def _make_client(
        catalog_xml: bytes = SYNTH_CATALOG_XML,
        law_xml_map: dict[str, bytes] | None = None,
        law_url_map: dict[str, bytes] | None = None,
    ):
        """Create a mock SourceClient that returns synthetic data.

        The mock needs to handle two types of calls:
        1. download(url) — raw bytes (catalog + law XML for adapter)
        2. download_with_headers(url) — DownloadResult (for execution service)
        """
        client = MagicMock(spec=SourceClient, instance=True)

        # Configure the policy to allow synthetic URLs
        real_policy = TransportPolicy(
            mode=TransportMode.TEST,
            allowed_hosts=("gesetze-im-internet.de", "localhost"),
            allowed_schemes=("https", "http"),
        )
        client.policy = real_policy

        _url_map = law_url_map or SYNTH_LAW_DOWNLOAD_URL_TO_XML
        _src_id_map = law_xml_map or SYNTH_LAW_URL_TO_XML

        def _download(url: str) -> bytes:
            if "gii-toc" in url:
                return catalog_xml
            for prefix, content in _url_map.items():
                if prefix in url or url.startswith(prefix):
                    return content
            raise SourceClientError(f"Unmocked download URL: {url}")

        def _download_with_headers(url: str) -> DownloadResult:
            for prefix, content in _src_id_map.items():
                if prefix in url:
                    return DownloadResult(
                        content=content,
                        http_status=200,
                        etag='"synth-etag-12345"',
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

        # Use side_effect so calls go through our functions
        client.download.side_effect = _download
        client.download_with_headers.side_effect = _download_with_headers
        client.download_verified.side_effect = _download_verified

        return client

    return _make_client


class TestApplySync:
    """I002: Apply sync integration tests."""

    def test_apply_creates_sync_run_with_dry_run_false(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify an apply run creates a SyncRun with dry_run=False."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()
        assert len(plan.items) > 0

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        sync_run = exec_service.execute(plan, dry_run=False)

        assert sync_run.dry_run is False
        assert sync_run.source_key == "gesetze-im-internet"

    def test_apply_downloads_and_imports_instruments(self, repo, mock_client_factory, snapshot_dir):
        """Verify instruments are downloaded and stored after apply."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        _ = exec_service.execute(plan, dry_run=False)

        # download_verified should have been called (RC-025-R1 F4: single-download contract)
        assert client.download_verified.call_count > 0, (
            "Expected download_verified to be called"
        )

        # Verify instruments are in the database
        instruments = repo.list_instruments()
        assert len(instruments) > 0, f"Expected instruments after apply, found {len(instruments)}"

        # Verify snapshots exist
        snapshots = repo.list_snapshots_for_source("gesetze-im-internet")
        assert len(snapshots) > 0, f"Expected snapshots after apply, found {len(snapshots)}"

    def test_apply_creates_sync_items_with_appropriate_statuses(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify sync_items are created with appropriate statuses after apply."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        sync_run = exec_service.execute(plan, dry_run=False)

        items = repo.get_items_for_run(sync_run.sync_run_id)
        assert len(items) > 0, "Expected sync items after apply"

        statuses = {item["item_status"] for item in items}
        # All items should be NEW for first-time apply
        assert "NEW" in statuses, f"Expected NEW items, got statuses: {statuses}"
        # No FAILED items expected
        failed_items = [i for i in items if i["item_status"] == "FAILED"]
        assert len(failed_items) == 0, f"Expected 0 FAILED items, got: {failed_items}"

    def test_apply_sync_run_summary_counts_are_correct(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify the SyncRun summary counts are correct after apply."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        sync_run = exec_service.execute(plan, dry_run=False)

        # Count items per status from DB
        items = repo.get_items_for_run(sync_run.sync_run_id)
        new_count = sum(1 for i in items if i["item_status"] == "NEW")
        changed_count = sum(1 for i in items if i["item_status"] == "CHANGED")

        assert sync_run.new_count == new_count, f"new_count: {sync_run.new_count} != {new_count}"
        assert sync_run.changed_count == changed_count, (
            f"changed_count: {sync_run.changed_count} != {changed_count}"
        )
        assert sync_run.total_in_catalog == len(plan.items), (
            f"total_in_catalog: {sync_run.total_in_catalog} != {len(plan.items)}"
        )

    def test_apply_status_is_completed_when_all_succeed(
        self, repo, mock_client_factory, snapshot_dir
    ):
        """Verify SyncRun status is COMPLETED when all items succeed."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        sync_run = exec_service.execute(plan, dry_run=False)

        assert sync_run.status == SyncRunStatus.COMPLETED
        assert sync_run.failed_count == 0

    def test_apply_persists_provisions_in_db(self, repo, mock_client_factory, snapshot_dir):
        """Verify provisions (law paragraphs) are persisted after apply."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        _ = exec_service.execute(plan, dry_run=False)

        provision_count = repo.count_provisions("gesetze-im-internet")
        assert provision_count > 0, f"Expected provisions after apply, found {provision_count}"

    def test_apply_sync_items_have_http_metadata(self, repo, mock_client_factory, snapshot_dir):
        """Verify sync items capture HTTP metadata (etag, last_modified)."""
        client = mock_client_factory()
        adapter = GiiAdapter(client, snapshot_dir)
        planning = SyncPlanningService(repo, client, adapter)

        plan = planning.plan()

        legal_service = LegalSourceService(repo, client, snapshot_dir)
        exec_service = SyncExecutionService(repo, legal_service, client, adapter)

        sync_run = exec_service.execute(plan, dry_run=False)

        items = repo.get_items_for_run(sync_run.sync_run_id)
        for item in items:
            if item["item_status"] not in ("SKIPPED", "REMOTE_MISSING"):
                assert item["http_status"] == 200, (
                    f"Expected http_status=200, got {item['http_status']}"
                )
                assert item["http_etag"] != "", "Expected non-empty http_etag"

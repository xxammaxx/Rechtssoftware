"""Integration tests for M7-B Phase 9 — Sync history on legal sources UI page."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings
from private_legal_navigator.domain.sync import SyncRun, SyncRunStatus


@pytest.fixture
def settings(tmp_path):
    data_dir = tmp_path / "pln_data"
    data_dir.mkdir()
    return Settings(data_dir=data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings) -> AsyncClient:
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as ac:
        yield ac


class TestLegalSourcesSyncHistory:
    """Tests for the sync history section on /ui/legal-sources (M7-B Phase 9)."""

    async def test_legal_sources_shows_truthful_sync_run_id(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """A displayed history row exposes the persisted run identifier."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)
        run = SyncRun(
            sync_run_id="SYNTHETISCH-ui-run-id",
            source_key="gesetze-im-internet",
            started_at="2026-07-26T12:00:00",
            completed_at="2026-07-26T12:05:00",
            status=SyncRunStatus.COMPLETED,
            dry_run=False,
            total_in_catalog=3,
            new_count=1,
            changed_count=1,
            unchanged_count=1,
            failed_count=0,
        )
        repo.save_sync_run(run)

        resp = await client.get("/ui/legal-sources")

        assert "Run-ID" in resp.text
        assert run.sync_run_id in resp.text
        assert "Gesamt" in resp.text
        assert "Unver&auml;ndert" in resp.text
        assert "26.07.2026 12:05" in resp.text

    async def test_legal_sources_page_renders(self, client: AsyncClient) -> None:
        """The legal sources page renders successfully."""
        resp = await client.get("/ui/legal-sources")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Rechtsquellenstatus" in resp.text

    async def test_legal_sources_has_sync_history_section(self, client: AsyncClient) -> None:
        """The legal sources page contains the sync history section."""
        resp = await client.get("/ui/legal-sources")
        assert "Synchronisationsverlauf" in resp.text

    async def test_legal_sources_empty_sync_history(self, client: AsyncClient) -> None:
        """When no sync runs exist, shows 'noch keine Synchronisation' message."""
        resp = await client.get("/ui/legal-sources")
        # The GII source is registered by default but never synced
        assert "Noch keine Synchronisation" in resp.text
        assert "Noch kein Rechtsquellenstand importiert" in resp.text

    async def test_legal_sources_catalog_stand_date_label(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """The catalog stand date uses the correct label, NOT 'Rechtsstand aktuell'."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        # Create a sync run with catalog_stand_date so the label appears
        run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-25T14:00:00",
            completed_at="2026-07-25T14:30:00",
            catalog_stand_date="2026-07-01",
            status=SyncRunStatus.COMPLETED,
            dry_run=False,
            total_in_catalog=600,
        )
        repo.save_sync_run(run)

        resp = await client.get("/ui/legal-sources")
        assert "Letzter erfolgreich importierter Quellenstand" in resp.text
        assert "Rechtsstand aktuell" not in resp.text

    async def test_legal_sources_shows_sync_history_after_runs(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """After sync runs are created, they appear in the sync history."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        # Create two sync runs for the GII source
        run1 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-25T14:00:00",
            completed_at="2026-07-25T14:30:00",
            catalog_stand_date="2026-07-01",
            catalog_url="https://www.gesetze-im-internet.de/gii-toc.xml",
            catalog_sha256="abc123",
            total_in_catalog=600,
            new_count=5,
            changed_count=3,
            unchanged_count=590,
            remote_not_modified_count=0,
            remote_missing_count=0,
            skipped_count=0,
            failed_count=2,
            status=SyncRunStatus.COMPLETED,
            dry_run=True,
            error_summary="",
        )
        run2 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-26T10:00:00",
            completed_at="2026-07-26T10:45:00",
            catalog_stand_date="2026-07-15",
            catalog_url="https://www.gesetze-im-internet.de/gii-toc.xml",
            catalog_sha256="def456",
            total_in_catalog=602,
            new_count=2,
            changed_count=8,
            unchanged_count=590,
            remote_not_modified_count=0,
            remote_missing_count=0,
            skipped_count=0,
            failed_count=0,
            status=SyncRunStatus.COMPLETED,
            dry_run=False,
            error_summary="",
        )
        repo.save_sync_run(run1)
        repo.save_sync_run(run2)

        # Also create a FAILED run
        run3 = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-26T11:00:00",
            completed_at="2026-07-26T11:05:00",
            catalog_stand_date="",
            status=SyncRunStatus.FAILED,
            dry_run=False,
            total_in_catalog=0,
            failed_count=1,
            error_summary="Connection timeout",
        )
        repo.save_sync_run(run3)

        resp = await client.get("/ui/legal-sources")

        assert resp.status_code == 200
        # Should show the sync runs
        assert "25.07.2026 14:00" in resp.text
        assert "26.07.2026 10:00" in resp.text
        # Should show the latest catalog stand date from COMPLETED run
        assert "2026-07-15" in resp.text
        # Should NOT show the empty state message
        assert "Noch keine Synchronisation" not in resp.text

    async def test_legal_sources_dry_run_vs_apply_display(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """Dry-run and apply runs are visually distinguished."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        # Create a dry-run
        dry_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-25T14:00:00",
            completed_at="2026-07-25T14:30:00",
            catalog_stand_date="2026-07-01",
            status=SyncRunStatus.COMPLETED,
            dry_run=True,
            total_in_catalog=600,
            new_count=3,
            changed_count=2,
        )
        repo.save_sync_run(dry_run)

        resp = await client.get("/ui/legal-sources")
        assert "Dry-Run" in resp.text
        # The last sync line should indicate dry-run
        assert "(Dry-Run)" in resp.text

    async def test_legal_sources_failed_status_display(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """Failed sync runs show 'fehlgeschlagen' status label."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        failed_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-26T10:00:00",
            completed_at="2026-07-26T10:05:00",
            status=SyncRunStatus.FAILED,
            dry_run=False,
            total_in_catalog=0,
            failed_count=1,
        )
        repo.save_sync_run(failed_run)

        resp = await client.get("/ui/legal-sources")
        assert "fehlgeschlagen" in resp.text

    async def test_legal_sources_no_external_resources(self, client: AsyncClient) -> None:
        """Legal sources page contains no external CDN, font, or script references."""
        resp = await client.get("/ui/legal-sources")
        # No CDN links
        assert "cdn." not in resp.text
        # No Google Fonts or Google APIs
        assert "googleapis" not in resp.text
        assert "fonts.googleapis" not in resp.text
        # No external JavaScript
        assert "<script src=" not in resp.text
        # No external CSS links (only local /static/ CSS)
        # Note: base_url values for sources are data, not external resources

    async def test_legal_sources_semantic_html(self, client: AsyncClient) -> None:
        """The page uses semantic HTML elements for accessibility."""
        resp = await client.get("/ui/legal-sources")
        assert 'lang="de"' in resp.text
        assert "<main" in resp.text

    async def test_legal_sources_human_review_disclaimer(self, client: AsyncClient) -> None:
        """The human review disclaimer is present in the footer."""
        resp = await client.get("/ui/legal-sources")
        assert "Menschliche Prüfung erforderlich" in resp.text

    async def test_legal_sources_aborted_status_display(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """Aborted sync runs show 'abgebrochen' status label."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        aborted_run = SyncRun(
            sync_run_id=str(uuid.uuid4()),
            source_key="gesetze-im-internet",
            started_at="2026-07-26T09:00:00",
            completed_at="2026-07-26T09:10:00",
            status=SyncRunStatus.ABORTED,
            dry_run=False,
            total_in_catalog=600,
        )
        repo.save_sync_run(aborted_run)

        resp = await client.get("/ui/legal-sources")
        assert "abgebrochen" in resp.text

    async def test_legal_sources_sync_history_absent_when_no_sources(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """Sync history section is not shown when no sources exist."""
        # Delete the default GII source from the DB
        from private_legal_navigator.infrastructure.database import get_connection

        conn = get_connection(settings.database_path)
        try:
            conn.execute("DELETE FROM legal_sources")
            conn.commit()
        finally:
            conn.close()

        resp = await client.get("/ui/legal-sources")
        assert resp.status_code == 200
        assert "Synchronisationsverlauf" not in resp.text
        assert "Keine Rechtsquellen registriert" in resp.text

    async def test_legal_sources_sync_run_count_display(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        """The sync run count is displayed correctly."""
        from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
            SqliteLegalSourceRepository,
        )

        repo = SqliteLegalSourceRepository(settings.database_path)

        # Create 2 runs
        for i in range(2):
            run = SyncRun(
                sync_run_id=str(uuid.uuid4()),
                source_key="gesetze-im-internet",
                started_at=f"2026-07-2{i + 5}T10:00:00",
                completed_at=f"2026-07-2{i + 5}T10:30:00",
                catalog_stand_date="2026-07-01",
                status=SyncRunStatus.COMPLETED,
                dry_run=i != 0,
                total_in_catalog=600 + i,
            )
            repo.save_sync_run(run)

        resp = await client.get("/ui/legal-sources")
        assert "Sync-L&auml;ufe: 2" in resp.text

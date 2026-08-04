"""Regression coverage for catalog-stand persistence after a successful apply."""

from unittest.mock import Mock

from private_legal_navigator.application.sync_service import SyncExecutionService
from private_legal_navigator.domain.sync import SyncItem, SyncItemStatus, SyncPlan, SyncRun


def test_successful_apply_persists_catalog_stand_on_source() -> None:
    """A non-dry apply records the known catalog stand against its source."""
    repo = Mock()
    repo.get_latest_sync_run.return_value = SyncRun(
        sync_run_id="SYNTHETISCH-run",
        source_key="gesetze-im-internet",
        started_at="2026-07-26T00:00:00+00:00",
        catalog_stand_date="2026-07-26",
    )
    service = SyncExecutionService(repo, Mock(), Mock(), Mock())
    plan = SyncPlan(
        sync_run_id="SYNTHETISCH-plan",
        catalog_stand_date="2026-07-26",
        items=[
            SyncItem(
                sync_item_id="SYNTHETISCH-item",
                sync_run_id="SYNTHETISCH-plan",
                source_identifier="SYNTHETISCH-source",
                item_status=SyncItemStatus.SKIPPED,
            )
        ],
    )

    completed = service.execute(plan, dry_run=False)

    assert completed.status.value == "COMPLETED"
    repo.update_legal_source_catalog_stand_date.assert_called_once_with(
        "gesetze-im-internet", "2026-07-26"
    )

"""Data Transfer Objects for legal source status and sync history display (M7-A.1, M7-B)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _format_iso_date(iso_str: str) -> str:
    """Format an ISO datetime string to DD.MM.YYYY HH:MM for display.

    Returns empty string if input is empty or unparseable.
    """
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        # Fallback: truncate to readable prefix
        return iso_str[:19] if len(iso_str) >= 19 else iso_str


@dataclass
class LegalSourceStatusDTO:
    """Rich status model for a legal source — real data, no placeholders."""

    source_key: str
    display_name: str
    authority_tier: str
    jurisdiction: str
    enabled: bool
    base_url: str
    description: str
    snapshot_count: int
    indexed_snapshot_count: int
    failed_snapshot_count: int
    instrument_count: int
    provision_count: int
    last_retrieved_at: str
    last_successful_import_at: str
    integrity_status: str  # NOT_VERIFIED, VERIFIED, FAILED, MISSING
    integrity_checked_at: str
    integrity_failure_count: int
    status_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "display_name": self.display_name,
            "authority_tier": self.authority_tier,
            "jurisdiction": self.jurisdiction,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "description": self.description,
            "snapshot_count": self.snapshot_count,
            "indexed_snapshot_count": self.indexed_snapshot_count,
            "failed_snapshot_count": self.failed_snapshot_count,
            "instrument_count": self.instrument_count,
            "provision_count": self.provision_count,
            "last_retrieved_at": self.last_retrieved_at,
            "last_successful_import_at": self.last_successful_import_at,
            "integrity_status": self.integrity_status,
            "integrity_checked_at": self.integrity_checked_at,
            "integrity_failure_count": self.integrity_failure_count,
            "status_warnings": self.status_warnings,
        }


@dataclass
class SyncRunSummary:
    """Summary of a single sync run for UI display (M7-B Phase 9).

    Provides a simplified, template-ready view of a SyncRun entity.
    All dates are pre-formatted to DD.MM.YYYY HH:MM.
    """

    run_id: str
    source_key: str
    status: str
    started_at: str
    finished_at: str
    total_items: int
    new_items: int
    changed_items: int
    unchanged_items: int
    skipped_items: int
    failed_items: int
    dry_run: bool
    catalog_stand_date: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_key": self.source_key,
            "status": self.status,
            "started_at": _format_iso_date(self.started_at),
            "finished_at": _format_iso_date(self.finished_at),
            "total_items": self.total_items,
            "new_items": self.new_items,
            "changed_items": self.changed_items,
            "unchanged_items": self.unchanged_items,
            "skipped_items": self.skipped_items,
            "failed_items": self.failed_items,
            "dry_run": self.dry_run,
            "catalog_stand_date": self.catalog_stand_date,
        }

    @classmethod
    def from_sync_run(cls, run: Any) -> "SyncRunSummary":
        """Create a summary from a SyncRun domain entity."""
        return cls(
            run_id=run.sync_run_id,
            source_key=run.source_key,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            started_at=run.started_at,
            finished_at=run.completed_at if run.completed_at else "",
            total_items=run.total_in_catalog,
            new_items=run.new_count,
            changed_items=run.changed_count,
            unchanged_items=run.unchanged_count,
            skipped_items=run.skipped_count,
            failed_items=run.failed_count,
            dry_run=run.dry_run,
            catalog_stand_date=run.catalog_stand_date if run.catalog_stand_date else "",
        )

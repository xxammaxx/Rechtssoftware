"""Domain models for M7-B incremental GII sync.

M7-B introduces sync run tracking, per-item status, and catalog
change management. All entities use append-only patterns — no
sync run or item is modified after creation except counter/status updates.
"""

from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class SyncRunStatus(str, Enum):
    """Status of a sync run execution.

    RUNNING: Currently executing (planning or applying).
    COMPLETED: All items processed successfully.
    ABORTED: User interrupted or system error.
    FAILED: All items processed, some or all failed.
    """

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class SyncItemStatus(str, Enum):
    """Status of a single instrument within a sync run.

    PENDING: Initial state before classification.
    NEW: In catalog, not in local corpus.
    KNOWN: In both catalog and local.
    CHANGED: In both catalog and local, SHA-256 differs.
    UNCHANGED: In both catalog and local, SHA-256 matches.
    REMOTE_NOT_MODIFIED: HTTP 304 response (Phase 2).
    REMOTE_MISSING: In local corpus but not in current catalog.
    SKIPPED: Skipped due to filter.
    FAILED: Download or import failed.
    """

    PENDING = "PENDING"
    NEW = "NEW"
    KNOWN = "KNOWN"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"
    REMOTE_NOT_MODIFIED = "REMOTE_NOT_MODIFIED"
    REMOTE_MISSING = "REMOTE_MISSING"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


# ──────────────────────────────────────────────
# Domain Entities
# ──────────────────────────────────────────────


@dataclass
class SyncRun:
    """A single execution of the sync pipeline.

    Records what happened during a sync operation: which source was synced,
    when it ran, what the catalog state was, and item-level outcomes.

    Attributes:
        sync_run_id: Unique identifier (UUID string).
        source_key: Which source was synced (e.g., 'gesetze-im-internet').
        started_at: When the sync run was initiated (ISO datetime).
        completed_at: When the sync run finished (empty if running).
        catalog_stand_date: The GII <stand> date at time of sync.
        catalog_url: The exact catalog URL that was fetched.
        catalog_sha256: SHA-256 of the catalog XML content (integrity).
        total_in_catalog: Total number of items in the catalog.
        new_count: Number of NEW items.
        changed_count: Number of CHANGED items.
        unchanged_count: Number of UNCHANGED items.
        remote_not_modified_count: Number of REMOTE_NOT_MODIFIED items.
        remote_missing_count: Number of REMOTE_MISSING items.
        skipped_count: Number of SKIPPED items.
        failed_count: Number of FAILED items.
        status: Current status of this sync run.
        dry_run: Whether this was a dry run (no actual changes).
        error_summary: Summary error message if status is FAILED or ABORTED.
    """

    sync_run_id: str
    source_key: str
    started_at: str
    completed_at: str = ""
    catalog_stand_date: str = ""
    catalog_url: str = ""
    catalog_sha256: str = ""
    total_in_catalog: int = 0
    new_count: int = 0
    changed_count: int = 0
    unchanged_count: int = 0
    remote_not_modified_count: int = 0
    remote_missing_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    status: SyncRunStatus = SyncRunStatus.RUNNING
    dry_run: bool = False
    error_summary: str = ""

    def __post_init__(self) -> None:
        if not self.sync_run_id:
            raise ValueError("sync_run_id must not be empty")
        if not self.source_key:
            raise ValueError("source_key must not be empty")
        if not self.started_at:
            raise ValueError("started_at must not be empty")


@dataclass
class SyncItem:
    """A single instrument's status within a sync run.

    Tracks the before-and-after state of one instrument during sync.

    Attributes:
        sync_item_id: Unique identifier (UUID string).
        sync_run_id: FK to SyncRun.
        source_identifier: Canonical URL of the instrument.
        abbreviation: Instrument abbreviation (e.g., 'BGB').
        title: Human-readable instrument title.
        item_status: Current status after sync planning/execution.
        previous_sha256: SHA-256 before this sync.
        new_sha256: SHA-256 after download.
        snapshot_id: FK to legal_source_snapshots (empty if none).
        instrument_id: FK to legal_instruments (empty if none).
        expression_id: FK to legal_expressions (empty if none).
        http_status: HTTP status code of the download attempt.
        http_etag: ETag header from the download response.
        http_last_modified: Last-Modified header from the download response.
        byte_size: Size of downloaded content in bytes.
        error_summary: Error message if item_status is FAILED.
        checked_at: When this item was processed (ISO datetime).
        retry_count: Number of retry attempts for this item.
    """

    sync_item_id: str
    sync_run_id: str
    source_identifier: str
    abbreviation: str = ""
    title: str = ""
    item_status: SyncItemStatus = SyncItemStatus.PENDING
    previous_sha256: str = ""
    new_sha256: str = ""
    snapshot_id: str = ""
    instrument_id: str = ""
    expression_id: str = ""
    http_status: int | None = None
    http_etag: str = ""
    http_last_modified: str = ""
    byte_size: int = 0
    error_summary: str = ""
    checked_at: str = ""
    retry_count: int = 0

    def __post_init__(self) -> None:
        if not self.sync_item_id:
            raise ValueError("sync_item_id must not be empty")
        if not self.sync_run_id:
            raise ValueError("sync_run_id must not be empty")
        if not self.source_identifier:
            raise ValueError("source_identifier must not be empty")


# ──────────────────────────────────────────────
# Value Objects
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class SyncPlan:
    """Result of the sync planning phase (value object, not persisted).

    Contains the full classification of all catalog items.
    Used to drive the execution (apply) phase.

    Attributes:
        sync_run_id: The sync run this plan belongs to.
        items: Classified sync items.
        warnings: Warning messages from the planning phase.
        estimated_download_bytes: Total estimated download size in bytes.
    """

    sync_run_id: str
    items: list[SyncItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_download_bytes: int = 0

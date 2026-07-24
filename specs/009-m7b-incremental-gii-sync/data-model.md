# Data Model — M7-B Incremental GII Sync & Corpus Change Management

## Overview

M7-B introduces two new domain entities (SyncRun, SyncItem) and adds one column to the existing `legal_sources` table. All M7-A tables remain unchanged.

**New entities:**
1. **SyncRun** — A single execution of the sync pipeline (plan + optional apply)
2. **SyncItem** — One instrument's status within a SyncRun

**New columns:**
- `legal_sources.last_catalog_stand_date` — tracks the last known catalog stand date

---

## Domain Entities

### Enums

```python
from enum import StrEnum

class SyncRunStatus(StrEnum):
    """Status of a sync run execution."""
    PLANNED = "PLANNED"          # Plan completed, not yet applied
    IN_PROGRESS = "IN_PROGRESS"  # Currently executing apply
    COMPLETED = "COMPLETED"      # All items processed successfully
    FAILED = "FAILED"            # All items processed, some/all failed
    ABORTED = "ABORTED"          # User interrupted or system error


class SyncItemStatus(StrEnum):
    """Status of a single instrument within a sync run."""
    PENDING = "PENDING"
    NEW = "NEW"                              # In catalog, not local
    CHANGED = "CHANGED"                      # In both, SHA-256 differs
    UNCHANGED = "UNCHANGED"                  # In both, SHA-256 matches
    REMOTE_NOT_MODIFIED = "REMOTE_NOT_MODIFIED"  # HTTP 304 (Phase 2)
    REMOTE_MISSING = "REMOTE_MISSING"        # In local, not in catalog
    SKIPPED = "SKIPPED"                      # Skipped (e.g., --instrument filter, --catalog-only)
    FAILED = "FAILED"                        # Download or import failed
```

### SyncRun

```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class SyncRun:
    """A single execution of the sync pipeline.

    Records what happened during a sync operation: which source was synced,
    when it ran, what the catalog state was, and what happened to each item.

    Attributes:
        run_id: Unique identifier for this sync run
        source_key: Which source was synced (e.g., 'gesetze-im-internet')
        started_at: When the sync run was initiated
        completed_at: When the sync run finished (None if still running)
        catalog_stand_date: The GII <stand> date at time of sync
        catalog_url: The exact catalog URL that was fetched
        catalog_sha256: SHA-256 of the catalog XML content (for integrity)
        total_items: Total number of items in the catalog
        new_count: Number of NEW items
        changed_count: Number of CHANGED items
        unchanged_count: Number of UNCHANGED items
        remote_missing_count: Number of REMOTE_MISSING items
        failed_count: Number of FAILED items
        skipped_count: Number of SKIPPED items
        status: Current status of this sync run
        dry_run: Whether this was a dry run (no actual changes)
        error_summary: Summary error message if status == FAILED/ABORTED
    """
    run_id: UUID | None
    source_key: str
    started_at: datetime
    completed_at: datetime | None = None
    catalog_stand_date: str = ""
    catalog_url: str = ""
    catalog_sha256: str = ""
    total_items: int = 0
    new_count: int = 0
    changed_count: int = 0
    unchanged_count: int = 0
    remote_not_modified_count: int = 0
    remote_missing_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    status: SyncRunStatus = SyncRunStatus.PLANNED
    dry_run: bool = True
    error_summary: str = ""

    def __post_init__(self) -> None:
        if self.run_id is None:
            self.run_id = uuid4()
        if not self.source_key:
            raise ValueError("source_key must not be empty")

    @property
    def item_counts(self) -> dict[str, int]:
        """Return a dict of all item status counts."""
        return {
            "total": self.total_items,
            "new": self.new_count,
            "changed": self.changed_count,
            "unchanged": self.unchanged_count,
            "remote_not_modified": self.remote_not_modified_count,
            "remote_missing": self.remote_missing_count,
            "failed": self.failed_count,
            "skipped": self.skipped_count,
        }

    @property
    def duration_seconds(self) -> float | None:
        """Duration in seconds, or None if still running."""
        if self.completed_at is None or self.started_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
```

### SyncItem

```python
@dataclass
class SyncItem:
    """A single instrument's status within a sync run.

    Tracks the before-and-after state of one instrument during sync.

    Attributes:
        item_id: Unique identifier for this sync item
        run_id: FK to SyncRun
        source_identifier: The instrument's source_identifier in the catalog
        abbreviation: Instrument abbreviation (e.g., 'BGB', 'SGB X')
        title: Human-readable instrument title
        item_status: Current status after sync planning/execution
        previous_sha256: SHA-256 before this sync (None if new)
        new_sha256: SHA-256 after download (None if not downloaded)
        snapshot_id: FK to legal_source_snapshots (if new snapshot created)
        instrument_id: FK to legal_instruments (if synced)
        http_status: HTTP status code of the download attempt
        http_etag: ETag header from the download response
        http_last_modified: Last-Modified header from the download response
        byte_size: Size of downloaded content in bytes
        error_summary: Error message if item_status == FAILED
    """
    item_id: UUID | None
    run_id: UUID
    source_identifier: str
    abbreviation: str = ""
    title: str = ""
    item_status: SyncItemStatus = SyncItemStatus.PENDING
    previous_sha256: str = ""
    new_sha256: str = ""
    snapshot_id: UUID | None = None
    instrument_id: UUID | None = None
    http_status: int = 0
    http_etag: str = ""
    http_last_modified: str = ""
    byte_size: int = 0
    error_summary: str = ""

    def __post_init__(self) -> None:
        if self.item_id is None:
            self.item_id = uuid4()
        if not self.source_identifier:
            raise ValueError("source_identifier must not be empty")
        if self.http_status < 0:
            raise ValueError("http_status must be >= 0")
        if self.byte_size < 0:
            raise ValueError("byte_size must be >= 0")
```

---

## Database Schema (Migration)

### New Table: sync_runs

```sql
CREATE TABLE IF NOT EXISTS sync_runs (
    run_id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL,
    started_at TEXT NOT NULL,          -- ISO 8601 UTC
    completed_at TEXT,                  -- ISO 8601 UTC (NULL if still running)
    catalog_stand_date TEXT NOT NULL DEFAULT '',
    catalog_url TEXT NOT NULL DEFAULT '',
    catalog_sha256 TEXT NOT NULL DEFAULT '',
    total_items INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    remote_not_modified_count INTEGER NOT NULL DEFAULT 0,
    remote_missing_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PLANNED',
    dry_run INTEGER NOT NULL DEFAULT 1,  -- 1 = dry run, 0 = apply
    error_summary TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sr_source_key ON sync_runs(source_key);
CREATE INDEX IF NOT EXISTS idx_sr_started_at ON sync_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_sr_status ON sync_runs(status);
```

### New Table: sync_items

```sql
CREATE TABLE IF NOT EXISTS sync_items (
    item_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES sync_runs(run_id) ON DELETE CASCADE,
    source_identifier TEXT NOT NULL,
    abbreviation TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    item_status TEXT NOT NULL DEFAULT 'PENDING',
    previous_sha256 TEXT NOT NULL DEFAULT '',
    new_sha256 TEXT NOT NULL DEFAULT '',
    snapshot_id TEXT REFERENCES legal_source_snapshots(snapshot_id) ON DELETE SET NULL,
    instrument_id TEXT REFERENCES legal_instruments(instrument_id) ON DELETE SET NULL,
    http_status INTEGER NOT NULL DEFAULT 0,
    http_etag TEXT NOT NULL DEFAULT '',
    http_last_modified TEXT NOT NULL DEFAULT '',
    byte_size INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_si_run_id ON sync_items(run_id);
CREATE INDEX IF NOT EXISTS idx_si_source_identifier ON sync_items(source_identifier);
CREATE INDEX IF NOT EXISTS idx_si_status ON sync_items(item_status);
```

### New Column: legal_sources.last_catalog_stand_date

```sql
ALTER TABLE legal_sources ADD COLUMN last_catalog_stand_date TEXT NOT NULL DEFAULT '';
```

This column stores the last seen `<stand>` date from the GII catalog. It enables the catalog stand-date gate: if the current catalog stand date matches the stored value, no items were added or removed from the catalog (but individual instrument content may still have changed — detected via SHA-256 comparison).

---

## Migration SQL

```sql
-- Migration: m7b_001_add_sync_tables

-- 1. New tables
CREATE TABLE IF NOT EXISTS sync_runs (
    run_id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    catalog_stand_date TEXT NOT NULL DEFAULT '',
    catalog_url TEXT NOT NULL DEFAULT '',
    catalog_sha256 TEXT NOT NULL DEFAULT '',
    total_items INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    remote_not_modified_count INTEGER NOT NULL DEFAULT 0,
    remote_missing_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PLANNED',
    dry_run INTEGER NOT NULL DEFAULT 1,
    error_summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sync_items (
    item_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES sync_runs(run_id) ON DELETE CASCADE,
    source_identifier TEXT NOT NULL,
    abbreviation TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    item_status TEXT NOT NULL DEFAULT 'PENDING',
    previous_sha256 TEXT NOT NULL DEFAULT '',
    new_sha256 TEXT NOT NULL DEFAULT '',
    snapshot_id TEXT REFERENCES legal_source_snapshots(snapshot_id) ON DELETE SET NULL,
    instrument_id TEXT REFERENCES legal_instruments(instrument_id) ON DELETE SET NULL,
    http_status INTEGER NOT NULL DEFAULT 0,
    http_etag TEXT NOT NULL DEFAULT '',
    http_last_modified TEXT NOT NULL DEFAULT '',
    byte_size INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT NOT NULL DEFAULT ''
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_sr_source_key ON sync_runs(source_key);
CREATE INDEX IF NOT EXISTS idx_sr_started_at ON sync_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_sr_status ON sync_runs(status);
CREATE INDEX IF NOT EXISTS idx_si_run_id ON sync_items(run_id);
CREATE INDEX IF NOT EXISTS idx_si_source_identifier ON sync_items(source_identifier);
CREATE INDEX IF NOT EXISTS idx_si_status ON sync_items(item_status);

-- 3. New column on legal_sources
-- Idempotent: use _migrate_add_column pattern from database.py
-- ALTER TABLE legal_sources ADD COLUMN last_catalog_stand_date TEXT NOT NULL DEFAULT '';
```

---

## State Machine

```
SyncItem Lifecycle (within one SyncRun):

                    fetch_catalog()
                         │
                    ┌─────▼──────┐
                    │  PENDING   │
                    └─────┬──────┘
                          │
              ┌───────────┴───────────┐
              │    plan_sync()        │
              └───────────┬───────────┘
                          │
          ┌───────────────┼───────────────────┐
          ▼               ▼                   ▼
      NEW (0)        KNOWN (1)          REMOTE_MISSING (2)
          │               │
          │          ┌────┴────┐
          │          ▼         ▼
          │    UNCHANGED   CHANGED
          │      (1a)        (1b)
          │                   │
          │           (--apply?)
          │               │
          ├───────────────┤
          │               │
          ▼               ▼
      download()      SKIP
          │
      ┌──┴──┐
      ▼     ▼
  SUCCESS FAILED
   (3)     (4)
```

**Where status values map to SyncItemStatus:**
- (0) NEW — nicht lokal vorhanden
- (1) KNOWN → (1a) UNCHANGED oder (1b) CHANGED
- (2) REMOTE_MISSING — lokal vorhanden, aber nicht mehr im Katalog
- (3) Nach Download: SyncItem erhält snapshot_id + new_sha256
- (4) FAILED — error_summary gesetzt

---

## SyncRun Lifecycle

```
PLANNED ──► IN_PROGRESS ──► COMPLETED
  │                            │
  └──► (never applied)        └──► FAILED (some items failed)
                                   │
                                   └──► ABORTED (user cancelled)
```

- **PLANNED:** SyncPlan erstellt, keine Änderungen vorgenommen
- **IN_PROGRESS:** Apply-Lauf läuft
- **COMPLETED:** Alle verarbeiteten Items erfolgreich
- **FAILED:** Mindestens ein Item fehlgeschlagen
- **ABORTED:** User hat abgebrochen oder Systemfehler

---

## Data Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  User (CLI)  │────►│ SyncPlanning    │────►│ SyncExecution    │
│  pln sync    │     │ Service         │     │ Service          │
└──────────────┘     └────────┬────────┘     └────────┬─────────┘
                              │                       │
                              ▼                       ▼
                     ┌─────────────────┐     ┌──────────────────┐
                     │ CatalogDiff     │     │ GiiAdapter       │
                     │ Engine          │     │ sync_instrument  │
                     │ (in-memory set  │     │ (download→hash→  │
                     │  comparison)    │     │  snapshot→parse) │
                     └─────────────────┘     └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │ SqliteSyncRun    │
                                             │ Repository       │
                                             │ (persist run +   │
                                             │  items)          │
                                             └──────────────────┘
```

---

## SyncPlan (Value Object)

The SyncPlan is the output of the planning phase. It is a value object (not persisted) that drives the execution phase.

```python
@dataclass(frozen=True)
class SyncPlan:
    """Result of the sync planning phase.
    
    Contains the full classification of all catalog items.
    Used to drive the execution (apply) phase.
    """
    source_key: str
    catalog_stand_date: str
    catalog_url: str
    catalog_sha256: str
    last_catalog_stand_date: str  # from legal_sources (empty if first sync)
    items: list[SyncItem]
    is_fresh: bool  # True if catalog changed since last sync

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.items),
            "new": sum(1 for i in self.items if i.item_status == SyncItemStatus.NEW),
            "changed": sum(1 for i in self.items if i.item_status == SyncItemStatus.CHANGED),
            "unchanged": sum(1 for i in self.items if i.item_status == SyncItemStatus.UNCHANGED),
            "remote_missing": sum(1 for i in self.items if i.item_status == SyncItemStatus.REMOTE_MISSING),
            "failed": sum(1 for i in self.items if i.item_status == SyncItemStatus.FAILED),
        }
```

---

## SourceClient Enhancement (DownloadResult)

The existing `SourceClient.download()` returns `bytes`. M7-B extends this to return a `DownloadResult` with header metadata:

```python
@dataclass
class DownloadResult:
    """Result of a download, including response metadata."""
    content: bytes
    etag: str = ""
    last_modified: str = ""
    status_code: int = 200
    content_type: str = ""
```

**Implementation sketch:**
- `SourceClient.download()` remains backward-compatible (returns bytes)
- `SourceClient.download_with_headers()` returns `DownloadResult` (new method)
- `GiiAdapter.sync_instrument()` uses `download_with_headers()` and passes ETag/Last-Modified to the snapshot entity and sync_item

---

## SQL Queries (Repository Port Operations)

```python
class SyncRunRepository(ABC):
    """Repository port for sync run persistence."""

    @abstractmethod
    def create_run(self, run: SyncRun) -> SyncRun: ...

    @abstractmethod
    def update_run(self, run: SyncRun) -> None: ...

    @abstractmethod
    def get_run(self, run_id: UUID) -> SyncRun | None: ...

    @abstractmethod
    def get_last_run(self, source_key: str) -> SyncRun | None: ...

    @abstractmethod
    def list_runs(self, source_key: str, limit: int = 10) -> list[SyncRun]: ...

    @abstractmethod
    def save_items(self, items: list[SyncItem]) -> None: ...

    @abstractmethod
    def get_items_for_run(self, run_id: UUID) -> list[SyncItem]: ...
```

# Spec — M7-B Incremental GII Sync & Corpus Change Management

## Feature
M7-B — Incremental synchronization with "Gesetze im Internet" (GII), catalog-based change detection, and corpus integrity management.

## Overview

M7-A established the legal source foundation: a full GII corpus download with SHA-256 snapshot integrity, FTS5 full-text search, and citation resolution. However, M7-A requires a **full re-download** of every instrument to detect changes — it downloads all ~5,000–6,100 catalog items unconditionally.

M7-B adds **incremental sync** capability: a catalog-based change detection layer that identifies new, changed, and removed instruments before downloading, reducing bandwidth, time, and server load. The sync operation is split into two phases:

1. **Plan Phase (always):** Compare catalog state against local state, classify every item, produce a sync plan without downloading any instrument data
2. **Execution Phase (apply only):** Download only items classified as NEW or CHANGED; skip UNCHANGED; log REMOTE_MISSING and FAILED

**Core principle:**
```
Catalog is the source of truth for "what exists."
SHA-256 is the source of truth for "what changed."
HTTP ETag/Last-Modified is the optimization (Phase 2).
```

M7-B introduces two new domain entities (`SyncRun`, `SyncItem`), a sync planning service with state machine, a dry-run mode for safe preview, and CLI entry points. All existing M7-A integrity guarantees (immutable snapshots, atomic import, SHA-256 dedup) are preserved and extended.

---

## Product Invariants

| ID | Invariant |
|----|-----------|
| INV-M7B-01 | Ein Sync-Lauf MUSS immer mit einem Plan beginnen. Es DARF keinen direkten "Apply ohne Plan"-Pfad geben. |
| INV-M7B-02 | Ein Dry-Run DARF keine Snapshots herunterladen, keine Datenbank-Einträge ändern und keine Dateien auf der Festplatte erstellen. |
| INV-M7B-03 | Ein Apply-Lauf DARF nur Items mit Status NEW oder CHANGED herunterladen. UNCHANGED-Items DÜRFEN nicht heruntergeladen werden. |
| INV-M7B-04 | Ein Sync-Lauf MUSS den catalog_stand_date der GII-Quelle vor und nach dem Lauf protokollieren. |
| INV-M7B-05 | Ein unterbrochener Sync-Lauf (Abbruch während des Downloads) MUSS wiederholbar sein. Bereits heruntergeladene Snapshots werden durch SHA-256-Dedup erkannt und nicht erneut verarbeitet. |
| INV-M7B-06 | Ein Sync-Lauf MUSS alle Items des Katalogs verarbeiten. Es DARF keine stillschweigende Auslassung geben (jedes Item bekommt einen Status). |
| INV-M7B-07 | Sync-Plan und Sync-Result MÜSSEN im selben Format dokumentiert sein (identische Felder, identische Typen). |
| INV-M7B-08 | Der Sync-Verlauf (sync_runs + sync_items) ist append-only. Ein gelöschter Sync-Lauf darf nicht wiederherstellbar sein (CASCADE DELETE). |
| INV-M7B-09 | Die HTTP-Header ETag und Last-Modified MÜSSEN pro Download erfasst und in der sync_items-Tabelle gespeichert werden. |
| INV-M7B-10 | Ein Force-Sync (--force) DARF die Katalog-Präsenz-Prüfung und den Stand-Date-Vergleich überspringen, aber MUSS weiterhin die SHA-256-Dedup-Prüfung durchführen. |
| INV-M7B-11 | Ein instrument-spezifischer Sync (--instrument KEY) darf NUR das angegebene Instrument verarbeiten, nicht den gesamten Katalog. |
| INV-M7B-12 | Der Sync darf KEINE Falldaten lesen, verarbeiten oder übertragen (Isolation aus ADR-007 Decision 7). |
| INV-M7B-13 | Der Sync-Verlauf (sync_runs, sync_items) enthält KEINE personenbezogenen Daten. |
| INV-M7B-14 | Sync-Verlauf muss mindestens 90 Tage aufbewahrt werden (Standard), konfigurierbar über Einstellungen. |
| INV-M7B-15 | Fehlgeschlagene Sync-Items (FAILED) MÜSSEN mit error_summary protokolliert werden und dürfen den Gesamtlauf nicht blockieren. |
| INV-M7B-16 | Ein abgeschlossener Sync-Lauf MUSS einen zusammenfassenden Bericht ausgeben: Gesamt, Neu, Geändert, Unverändert, Remote-Fehler, Fehlgeschlagen. |
| INV-M7B-17 | Der Sync-Lauf MUSS in der legal_sources-Tabelle den letzten catalog_stand_date speichern. |
| INV-M7B-18 | Die Zustandsmaschine eines SyncItems DARF keine ungültigen Übergänge erlauben (z.B. NEW → UNCHANGED ohne erneuten Katalogvergleich). |

---

## Data Integrity Invariants

| ID | Invariant |
|----|-----------|
| DI-M7B-01 | Jeder SyncRun hat einen eindeutigen Primärschlüssel (UUID) und einen source_key, der auf einen gültigen Eintrag in legal_sources verweist. |
| DI-M7B-02 | SyncRun.completed_at DARF nur gesetzt werden, wenn SyncRun.status = "COMPLETED" oder "FAILED" ist. |
| DI-M7B-03 | Jedes SyncItem hat einen eindeutigen Primärschlüssel (UUID) und eine referenzielle Integrität zu genau einem SyncRun (sync_run_id FK). |
| DI-M7B-04 | SyncItem.item_status MUSS einer der folgenden Werte sein: PENDING, NEW, CHANGED, UNCHANGED, REMOTE_NOT_MODIFIED, REMOTE_MISSING, SKIPPED, FAILED. |
| DI-M7B-05 | Ein SyncItem mit item_status = "FAILED" MUSS einen nicht-leeren error_summary haben. |
| DI-M7B-06 | SyncItem.previous_sha256 DARF nur NULL sein, wenn das Item im vorherigen Lauf nicht existierte (item_status = "NEW"). |
| DI-M7B-07 | SyncItem.new_sha256 MUSS NULL sein, wenn kein Download stattfand (item_status = "UNCHANGED" oder "REMOTE_NOT_MODIFIED" oder "REMOTE_MISSING"). |
| DI-M7B-08 | SyncItem.snapshot_id MUSS auf legal_source_snapshots.snapshot_id verweisen, wenn ein neuer Snapshot erstellt wurde. Falls nicht (UNCHANGED / REMOTE_NOT_MODIFIED), DARF snapshot_id NULL sein. |
| DI-M7B-09 | SyncItem.instrument_id DARF NULL sein, wenn das Instrument lokal nicht existiert (z.B. REMOTE_MISSING ohne lokale Kopie). |
| DI-M7B-10 | Alle Zeitstempel in sync_runs und sync_items MÜSSEN im ISO-8601-Format (UTC) vorliegen. |

---

## User Stories

### US1 — Corpus auf Aktualität prüfen (P1)
Als Nutzer möchte ich schnell feststellen können, ob mein lokaler Rechtskorpus auf dem neuesten Stand ist.

**Acceptance Criteria:**
- Der Nutzer kann einen Sync-Plan anfordern, der den GII-Katalog mit dem lokalen Stand vergleicht
- Der Plan zeigt: Gesamtanzahl, neu, geändert, unverändert und entfernte Instrumente
- Der Plan enthält den aktuellen catalog_stand_date von GII
- Der Plan vergleicht den lokalen last_catalog_stand_date und zeigt eine Warnung, wenn dieser veraltet ist
- Der Plan wird OHNE Download von Instrument-Daten erstellt

### US2 — Korpus aktualisieren (P1)
Als Nutzer möchte ich meinen Korpus auf den neuesten Stand bringen können.

**Acceptance Criteria:**
- Der Nutzer kann einen Apply-Lauf ausführen, der nur neue/geänderte Instrumente herunterlädt
- Unveränderte Instrumente werden nicht heruntergeladen
- Heruntergeladene Instrumente werden normal importiert (SHA-256 geprüft, in SQLite gespeichert, FTS5 indiziert)
- Nach Abschluss wird ein zusammenfassender Bericht angezeigt
- Der Bericht wird in der Datenbank persistiert

### US3 — Dry-Run: Änderungen vorab prüfen (P1)
Als Nutzer möchte ich sehen, welche Änderungen ein Sync-Lauf vornehmen würde, OHNE dass tatsächlich Daten heruntergeladen werden.

**Acceptance Criteria:**
- Dry-Run erzeugt einen vollständigen Sync-Plan
- Es wird KEIN Instrument heruntergeladen
- Es werden KEINE Snapshots erstellt
- Es werden KEINE Datenbankeinträge geändert
- Der Sync-Plan wird dem Nutzer wie ein Apply-Bericht angezeigt
- Der Dry-Run wird NICHT in der Datenbank persistiert

### US4 — Unterbrechungsfestigkeit (P1)
Als Nutzer möchte ich, dass ein unterbrochener Sync-Lauf beim erneuten Start nicht von vorne beginnt, sondern dort weitermacht, wo er aufgehört hat.

**Acceptance Criteria:**
- Wird der Sync während des Downloads unterbrochen, sind bereits heruntergeladene Snapshots auf der Festplatte vorhanden
- Ein erneuter Sync (apply) mit demselben oder neueren Katalog erkennt diese Snapshots über SHA-256-Dedup
- Bereits verarbeitete Instrumente werden nicht erneut heruntergeladen
- Der Sync-Verlauf wird append-only gespeichert — ein neuer Lauf erzeugt immer einen neuen SyncRun

### US5 — Instrument-Spezifischer Sync (P2)
Als Nutzer möchte ich ein einzelnes Instrument gezielt aktualisieren können, ohne den gesamten Korpus zu durchlaufen.

**Acceptance Criteria:**
- Der Nutzer kann `--instrument KEY` angeben, um nur ein bestimmtes Instrument zu synchronisieren
- Die Katalog-Präsenz-Prüfung erfolgt trotzdem (das Instrument muss im Katalog existieren)
- Der Sync-Plan enthält nur dieses eine Instrument
- Der Apply-Lauf verarbeitet nur dieses eine Instrument

### US6 — Sync-Verlauf einsehen (P2)
Als Nutzer möchte ich die letzten Sync-Läufe und deren Ergebnisse einsehen können.

**Acceptance Criteria:**
- Der Nutzer kann die letzten N Sync-Läufe auflisten
- Jeder Sync-Lauf zeigt: Startzeit, Endzeit, Dauer, Status, Zusammenfassung (neu/geändert/unverändert/fehlgeschlagen)
- Der Nutzer kann Details eines einzelnen Sync-Laufs anzeigen
- Details enthalten jedes verarbeitete Item mit individuellem Status

### US7 — Integrität prüfen (P2)
Als Nutzer möchte ich die Integrität meines Korpus nach einem Sync überprüfen können.

**Acceptance Criteria:**
- Der Nutzer kann `verify` ausführen, der alle Snapshots auf SHA-256-Integrität prüft
- Der Bericht zeigt: geprüft, bestanden, fehlgeschlagen, fehlend
- Fehlgeschlagene Snapshots werden mit Hash-Differenz protokolliert
- Der Befehl ändert KEINE Daten

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-M7B-001 | Das System MUSS einen Sync-Plan aus dem GII-Katalog und dem lokalen Zustand erstellen können. |
| FR-M7B-002 | Der Sync-Plan MUSS jedes Item des Katalogs klassifizieren (NEW, CHANGED, UNCHANGED, REMOTE_NOT_MODIFIED, REMOTE_MISSING). |
| FR-M7B-003 | Die Klassifikation MUSS auf SHA-256-Vergleich zwischen lokalem Snapshot und remoteem Snapshot basieren. |
| FR-M7B-004 | Die Klassifikation MUSS den catalog_stand_date der Quelle berücksichtigen. |
| FR-M7B-005 | Ein Apply-Lauf DARF NUR Items mit Status NEW oder CHANGED herunterladen. |
| FR-M7B-006 | Ein Apply-Lauf MUSS SHA-256-Dedup vor dem Import durchführen (existierender Snapshot mit gleichem Hash wird nicht erneut importiert). |
| FR-M7B-007 | Ein Dry-Run DARF KEINE Downloads, keine Snapshots und keine Datenbankänderungen durchführen. |
| FR-M7B-008 | Ein Force-Sync (--force) MUSS die Stand-Date-Prüfung überspringen. |
| FR-M7B-009 | Der Sync-Verlauf MUSS in der Datenbank persistiert werden (sync_runs + sync_items). |
| FR-M7B-010 | Der Sync-Verlauf MUSS append-only sein. |
| FR-M7B-011 | Der Sync-Lauf MUSS HTTP-ETag und Last-Modified pro Download erfassen. |
| FR-M7B-012 | Das System MUSS die SourceClient-Klasse um Header-Erfassung erweitern (ETag, Last-Modified). |
| FR-M7B-013 | Ein Sync-Lauf MUSS den catalog_stand_date vor dem Lauf und nach dem Lauf protokollieren. |
| FR-M7B-014 | Das System MUSS legal_sources.last_catalog_stand_date nach einem erfolgreichen Apply-Lauf aktualisieren. |
| FR-M7B-015 | Das System MUSS einen zusammenfassenden Bericht nach jedem Apply-Lauf ausgeben. |
| FR-M7B-016 | Der Sync Befehl MUSS die CLI-Konventionen (pln sync --help) unterstützen. |
| FR-M7B-017 | Der Sync-Status Befehl MUSS die letzten N Sync-Läufe anzeigen. |
| FR-M7B-018 | Der Sync-Verify Befehl MUSS die Snapshot-Integrität prüfen. |
| FR-M7B-019 | Ein fehlgeschlagenes Item DARF den gesamten Sync-Lauf nicht zum Scheitern bringen. |
| FR-M7B-020 | Nach Abschluss eines Apply-Laufs MUSS der Nutzer eine Zusammenfassung erhalten. |

---

## State Machine

```
SyncItem Lifecycle (during a sync run):

                    ┌─────────────────────────────────────┐
                    │         Catalog Presence Diff        │
                    │         (catalog vs local state)     │
                    └────────────┬────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
        NEW (im Katalog,   KNOWN (im Katalog,   REMOTE_MISSING
        nicht lokal)       auch lokal)           (nicht mehr im
            │                    │                Katalog, aber
            │                    │                lokal vorhanden)
            │                    │
            │           ┌────────┴────────┐
            │           ▼                 ▼
            │      SHA-256 gleich?   SHA-256 verschieden?
            │           │                 │
            │           ▼                 ▼
            │      UNCHANGED          CHANGED
            │                         (wenn --apply:
            │                          download + reimport)
            │
            ▼
      (wenn --apply: download + import)
            │
            ▼
         SUCCESS / FAILED
```

**Full state enum:**

```python
class SyncItemStatus(StrEnum):
    PENDING = "PENDING"                    # Initial state
    NEW = "NEW"                            # New in catalog, not local
    CHANGED = "CHANGED"                    # In catalog AND local, but SHA-256 differs
    UNCHANGED = "UNCHANGED"                # In catalog AND local, SHA-256 matches
    REMOTE_NOT_MODIFIED = "REMOTE_NOT_MODIFIED"  # HTTP 304 (Phase 2)
    REMOTE_MISSING = "REMOTE_MISSING"      # In local, NOT in catalog
    SKIPPED = "SKIPPED"                    # Skipped (e.g., --instrument filter)
    FAILED = "FAILED"                      # Download or import failed
```

**Valid transitions:**
- PENDING → NEW, CHANGED, UNCHANGED, REMOTE_NOT_MODIFIED, REMOTE_MISSING, SKIPPED, FAILED
- NEW → FAILED (download failed)
- CHANGED → FAILED (download or import failed)

---

## Non-Goals (explicitly out of scope)

- Binary diffs (delta download between versions)
- HTTP 304/conditional request optimization (Phase 2, deferred to M7-B+)
- Automatic/scheduled sync (background cron job)
- Multi-source orchestration (only GII in M7-B; BGBl, EUR-Lex adapters not affected)
- Incremental FTS5 index rebuild (FTS5 is synchronous — content changes propagate automatically)
- Sync compression or bandwidth limiting
- Rollback of individual sync operations
- Distributed sync coordination
- Email/notification on sync completion
- Sync validation against external checkers
- Snapshot garbage collection (removal of superseded snapshots)

---

## Security Boundaries

| Threat | Mitigation |
|--------|------------|
| Catalog manipulation (mitm) | HTTPS-only, SHA-256 integrity check on catalog download |
| Replay attack (stale catalog) | catalog_stand_date comparison against last known good date |
| Denial of service through huge catalog | Max catalog size limit (10 MB) enforced in SourceClient |
| Path traversal via instrument key | Key validation: only allow alphanumeric + underscore + hyphen |
| Resource exhaustion (too many items) | Apply-limit check: max 500 items per sync run (configurable) |
| Log injection via error_summary | Safe logging: error_summary truncated to 500 chars, no newlines |
| Data leak in sync logs | No case data, no personal data, no snapshot content in logs |

---

## CLI Contract Summary

```
Usage:
    pln sync gii [--dry-run|--apply] [--instrument KEY] [--catalog-only] [--force]
    pln sync status [--source KEY] [--last N]
    pln sync verify [--source KEY]

Flags:
    --dry-run           Plan only, no downloads, no DB changes (default if neither --dry-run nor --apply)
    --apply             Execute the plan: download NEW/CHANGED items
    --instrument KEY    Sync only a specific instrument (by abbreviation or catalog key)
    --catalog-only      Only fetch and display catalog info (no per-item classification)
    --force             Skip catalog_stand_date comparison and SHA-256 staleness check
    --source KEY        Source identifier (default: gesetze-im-internet)
    --last N            Show last N sync runs (default: 1)
```

See [contracts/sync-cli.md](contracts/sync-cli.md) for the full CLI contract.

---

## Affected Layers

| Layer | Changes |
|-------|---------|
| **Domain** | New entities: SyncRun, SyncItem, SyncItemStatus, SyncRunStatus enum |
| **Application** | New services: SyncPlanningService, SyncExecutionService; modified: LegalSourceService (delegation) |
| **Infrastructure** | New repository: SqliteSyncRunRepository; modified: SourceClient (ETag/Last-Modified capture), GiiAdapter (catalog_stand_date extraction) |
| **API** | New CLI entry points; UI status page updates |
| **Database** | New tables: sync_runs, sync_items; new column: legal_sources.last_catalog_stand_date |

---

## Dependencies

- None beyond existing M7-A dependencies (lxml, httpx, SQLite)
- No new external packages
- Phase 2 (HTTP 304) requires no additional dependencies — httpx already supports conditional headers

---

## Glossary

| Term | Definition |
|------|------------|
| **SyncRun** | A single execution of the sync pipeline (plan + optional apply). Persisted in sync_runs. |
| **SyncItem** | A single instrument's status within a SyncRun. One SyncItem per catalog item per run. |
| **Catalog Stand Date** | The GII `<stand>` date in gii-toc.xml, indicating when the catalog metadata was last updated. |
| **Catalog Presence Diff** | Comparison of "what exists in the catalog" vs "what exists locally" — identifies new and removed items. |
| **Conditional Request** | HTTP request with `If-None-Match` (ETag) or `If-Modified-Since` (Last-Modified) header. Server returns 304 if unchanged. Deferred to Phase 2. |
| **Force Sync** | `--force` flag to bypass the catalog_stand_date gate. Used when the user explicitly wants to re-check all items. |

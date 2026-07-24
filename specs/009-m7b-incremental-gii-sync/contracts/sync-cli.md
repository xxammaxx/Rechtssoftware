# CLI Contract — M7-B Incremental GII Sync

## Base Command

```
pln sync
```

The `pln` command is the root CLI entry point for PrivateLegalNavigator. Subcommands are organized hierarchically.

---

## Subcommands

### 1. sync gii — Sync GII Legal Source

```
pln sync gii [--dry-run|--apply] [--instrument KEY] [--catalog-only] [--force]
```

**Description:** Synchronize the local legal corpus with the "Gesetze im Internet" source. By default (no flag), runs in dry-run mode (plan only).

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | flag | implicit default | Plan only: show what would change without downloading. **Default if neither `--dry-run` nor `--apply` is specified.** |
| `--apply` | flag | — | Execute the sync plan: download NEW/CHANGED instruments, update database. |
| `--instrument KEY` | string | — | Only process the instrument identified by KEY (abbreviation or catalog key). Overrides full catalog sync. |
| `--catalog-only` | flag | — | Only fetch and display catalog info. No per-item classification. No downloads. |
| `--force` | flag | — | Skip catalog_stand_date comparison. Force re-classification of all items. |

**Mutually exclusive:** `--dry-run` and `--apply` are mutually exclusive. If both are provided, `--apply` takes precedence with a warning.

**Examples:**

```bash
# Default: dry-run (plan only)
pln sync gii

# Explicit dry-run
pln sync gii --dry-run

# Apply changes
pln sync gii --apply

# Sync only BGB
pln sync gii --apply --instrument BGB

# Catalog info only
pln sync gii --catalog-only

# Force re-check
pln sync gii --dry-run --force
```

**Output:**

- `--dry-run` or default: See [sync-plan.md](sync-plan.md)
- `--apply`: See [sync-result.md](sync-result.md)
- `--catalog-only`: Catalog metadata display (stand_date, item count, source info)

---

### 2. sync status — Show Sync History

```
pln sync status [--source KEY] [--last N]
```

**Description:** Display the history of sync runs for a given source.

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--source KEY` | string | `gesetze-im-internet` | Source identifier |
| `--last N` | int | `1` | Number of most recent runs to display |

**Examples:**

```bash
# Show last sync run
pln sync status

# Show last 5 runs with details
pln sync status --last 5

# Show status for a different source (future: BGBl)
pln sync status --source bundesgesetzblatt --last 3
```

**Output format:**

```
Sync History for: gesetze-im-internet
───────────────────────────────────────────────────────────────
Run        Date                Status    Total  New  Chg  Unch  Fail  Duration
─────      ────                ──────    ─────  ───  ───  ────  ────  ────────
abc123     2026-07-24 10:00    COMPLETED 6120     0   12  6108     0  4m32s
def456     2026-07-20 08:30    COMPLETED 6105  6105    0     0     0  28m15s

Last catalog stand date: 24. Juli 2026 (2026-07-24)
```

---

### 3. sync verify — Verify Snapshot Integrity

```
pln sync verify [--source KEY]
```

**Description:** Verify the SHA-256 integrity of all stored snapshots for a source. Compares the stored hash against on-disk content.

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--source KEY` | string | `gesetze-im-internet` | Source identifier |

**Examples:**

```bash
# Verify all GII snapshots
pln sync verify

# Verify snapshots for a specific source
pln sync verify --source bundesgesetzblatt
```

**Output format:**

```
Verifying snapshots for: gesetze-im-internet
────────────────────────────────────────────────────────────────
  Checking 6120 snapshots...
  Verified: 6120
  Failed:   0
  Missing:  0
  Status:   ALL INTEGRITY CHECKS PASSED
────────────────────────────────────────────────────────────────
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (plan created, apply completed, all items OK) |
| 1 | Partial success (some items failed, overall run completed) |
| 2 | Fatal error (could not start sync: network error, catalog parse error) |
| 3 | Invalid arguments (bad flag combination) |
| 4 | Sync already in progress (concurrent run detected) |

See [status-codes.md](status-codes.md) for the full status code reference.

---

## Global Flags

| Flag | Description |
|------|-------------|
| `--help` | Show help and exit |
| `--version` | Show version and exit |
| `--verbose` | Verbose output (debug-level logging) |
| `--quiet` | Minimal output (errors only) |

---

## Argument Validation

| Argument | Validation |
|----------|------------|
| `--instrument KEY` | Must match `/^[a-zA-Z0-9_ -]+$/`. Rejected with error message if invalid. |
| `--last N` | Must be integer >= 1 and <= 100. Default: 1. |
| `--source KEY` | Must match a registered legal_source.source_key. Default: gesetze-im-internet. |

---

## Help Text

```
Usage:
    pln sync gii [--dry-run|--apply] [--instrument KEY] [--catalog-only] [--force]
    pln sync status [--source KEY] [--last N]
    pln sync verify [--source KEY]

Incremental GII synchronization.

Commands:
    gii        Sync with "Gesetze im Internet" legal source
    status     Show sync run history
    verify     Verify snapshot integrity

Use "pln sync <command> --help" for more information about a command.
```

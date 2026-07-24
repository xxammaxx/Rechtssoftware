# Accessibility Requirements — M7-B CLI Output

## Overview

M7-B is primarily a CLI feature. Accessibility requirements focus on terminal output readability, screen reader compatibility, and internationalization.

---

## General Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| A-01 | CLI output MUST use Unicode box-drawing characters only as decoration, not as sole information carriers. Plain text fallback MUST show same information. | HIGH |
| A-02 | All status information MUST be available in plain text (not only colored/emojis). | HIGH |
| A-03 | Error messages MUST be in plain text without ANSI escape codes. | HIGH |
| A-04 | Progress indicators MUST have a non-TTY fallback (log lines instead of spinner). | HIGH |
| A-05 | All CLI output MUST be UTF-8 encoded. | MEDIUM |
| A-06 | Timestamps MUST be in ISO 8601 format for machine readability. | MEDIUM |
| A-07 | Numeric values MUST use locale-independent formatting (no thousands separators). | MEDIUM |
| A-08 | Summary tables MUST not rely on column alignment alone — row labels MUST be unique identifiers. | MEDIUM |

---

## Color and Emoji Usage

| Element | With TTY | Without TTY |
|---------|----------|-------------|
| ✅ Success | Green + ✅ | `[OK]` |
| ❌ Failure | Red + ❌ | `[FAIL]` |
| ⚠️ Warning | Yellow + ⚠️ | `[WARN]` |
| ⏭️ Skipped | Gray + ⏭️ | `[SKIP]` |
| ℹ️ Info | Blue + ℹ️ | `[INFO]` |

**Rule:** Every color/emoji indicator MUST be accompanied by a text equivalent that is shown regardless of TTY.

---

## Output Format for Screen Readers

| Scenario | Format |
|----------|--------|
| Sync plan summary | Plain text table with header row |
| Sync result summary | Plain text table with header row |
| Per-item details | One item per line: `[STATUS] identifier — description` |
| Error messages | `ERROR: <message>` on first line, details indented below |
| Progress | `[1/6120] Downloading BGB...` (unique per line) |

---

## Language

| ID | Requirement | Priority |
|----|-------------|----------|
| L-01 | CLI help text MUST be available in German. | HIGH |
| L-02 | All user-facing messages (status, results, errors) MUST be in German. | HIGH |
| L-03 | Machine-readable JSON output MUST use English field names. | MEDIUM |
| L-04 | No hardcoded English-only strings in user-facing paths. | MEDIUM |

---

## Help Accessibility

| ID | Requirement | Priority |
|----|-------------|----------|
| H-01 | `--help` MUST show complete usage, all flags with descriptions, and one example per subcommand. | HIGH |
| H-02 | Help text MUST use consistent indentation and capitalisation. | MEDIUM |
| H-03 | Example commands MUST be reproducible (copy-paste ready). | MEDIUM |
| H-04 | Long options (`--apply`) MUST always have short aliases where practical. | LOW |

---

## Error Accessibility

| ID | Requirement | Priority |
|----|-------------|----------|
| E-01 | Every error MUST include: error code, human-readable message, suggested action. | HIGH |
| E-02 | Stack traces MUST NOT be shown in CLI output (use `--verbose` for debug). | HIGH |
| E-03 | Network errors MUST distinguish between "cannot reach server" and "server returned error". | MEDIUM |
| E-04 | Fatal errors MUST include the exact command that failed and a suggested fix. | MEDIUM |

---

## Summary of Accessible Output Patterns

```
# Good (accessible):
[OK]   BGB — Bürgerliches Gesetzbuch (2.3 MB heruntergeladen)
[OK]   StGB — Strafgesetzbuch (1.1 MB heruntergeladen)
[SKIP] VwGO — Verwaltungsgerichtsordnung (unverändert)

# Bad (inaccessible with color only):
✅ BGB
✅ StGB
⏭️ VwGO
```

The text prefix `[OK]` / `[SKIP]` carries the same information as the emoji, making the output accessible without color support.

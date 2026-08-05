# V1.0 Definition of Done — PrivateLegalNavigator

**Version:** v1.0.0-rc.2
**Date:** 2026-07-26
**Branch:** `release/v1-installable-closure`

---

## 1. Product Requirements (MUST)

### 1.1 Core Identity
- [ ] Local single-user desktop application
- [ ] Binds exclusively to `127.0.0.1` by default (no `0.0.0.0`)
- [ ] No cloud processing, no telemetry, no analytics
- [ ] No automatic legal decisions
- [ ] All legally relevant output requires explicit human review

### 1.2 Feature Completeness (Golden Path)
- [ ] Create case
- [ ] Upload PDF document (MIME-type validation, 20 MB limit)
- [ ] Extract text from text-based PDFs (pymupdf, fully local)
- [ ] Classify document (Bescheid, Rechnung, Mahnung, etc.)
- [ ] Detect deadline candidates
- [ ] Identify reference event candidates
- [ ] Confirm/reject/manual reference date
- [ ] Correct/revoke confirmations (append-only history)
- [ ] Show non-binding calculation preview
- [ ] Show deterministic calculation trace
- [ ] Import/reference GII legal sources (gesetze-im-internet.de)
- [ ] FTS5 full-text search across legal corpus
- [ ] Citation resolution (§ 70 VwGO → norm text)
- [ ] Link norms to cases (case-legal-links)
- [ ] Create legal timeline events
- [ ] Confirm/correct/revoke timeline events
- [ ] View exportable evidence pack

### 1.3 Data Integrity
- [ ] Persistent local data survives application restart
- [ ] Data directory separate from installation directory
- [ ] UUID-based document storage with path traversal protection
- [ ] SHA-256 snapshot integrity for legal sources
- [ ] Append-only confirmation history (no deletion)
- [ ] Schema migration is automatic on startup

### 1.4 Backup & Restore
- [ ] Script-based backup of SQLite + documents + snapshots
- [ ] Backup manifest with SHA-256 checksums
- [ ] Restore with integrity validation
- [ ] Restore does not overwrite existing data without warning
- [ ] Version incompatibility detection
- [ ] Real restore test passed (empty environment)

---

## 2. Quality Requirements (MUST)

### 2.1 Test Suite
- [ ] All tests pass (currently 906, minimum maintained)
- [ ] No skipped tests without documented reason
- [ ] Overall coverage ≥ 71% (current baseline, never decreases)
- [ ] New v1.0 modules ≥ 90% coverage

### 2.2 Static Analysis
- [ ] `ruff check src tests` — 0 errors
- [ ] `mypy src` — 0 errors (strict mode)
- [ ] `pip check` — 0 conflicts

### 2.3 Packaging
- [ ] `python -m build` produces wheel and sdist
- [ ] `twine check dist/*` — PASS
- [ ] Wheel contains all templates, CSS, static files
- [ ] Wheel does NOT contain: .env, databases, real case data, logs, secrets

### 2.4 Installation
- [ ] Installation from wheel succeeds in fresh venv (no --editable)
- [ ] Installation without Git repository present
- [ ] CLI entry point `private-legal-navigator` works after install
- [ ] Application starts and `/health` responds
- [ ] Browser UI loads correctly

### 2.5 Windows Pilot Package
- [ ] `install.ps1` — idempotent, no admin rights required
- [ ] `start.ps1` — binds to 127.0.0.1, opens browser
- [ ] `stop.ps1` — only kills own process
- [ ] `backup.ps1` — consistent backup
- [ ] `restore.ps1` — validates and restores
- [ ] `uninstall.ps1` — keeps data by default, optional purge

---

## 3. Release Requirements (MUST)

### 3.1 Version Consistency
- [ ] `pyproject.toml` version: `1.0.0rc2` (PEP 440)
- [ ] Git tag: `v1.0.0-rc.2`
- [ ] `CHANGELOG.md` updated with v1.0.0-rc.2 entry
- [ ] `README.md` reflects actual test counts, coverage, and version
- [ ] All version sources consistent

### 3.2 Documentation
- [ ] `README.md` — accurate and verified
- [ ] `CHANGELOG.md` — complete v1.0 entry
- [ ] `docs/user/INSTALL-WINDOWS.md` — non-developer readable
- [ ] `docs/user/FIRST-START.md`
- [ ] `docs/user/USER-GUIDE.md`
- [ ] `docs/user/BACKUP-RESTORE.md`
- [ ] `docs/user/UPGRADE.md`
- [ ] `docs/user/UNINSTALL.md`
- [ ] `docs/user/TROUBLESHOOTING.md`
- [ ] `docs/user/KNOWN-LIMITATIONS.md`
- [ ] `docs/release/V1-RELEASE-CHECKLIST.md`
- [ ] `docs/release/V1-VALIDATION-REPORT.md`

### 3.3 Release Artifacts
- [ ] `dist/private_legal_navigator-1.0.0rc2-py3-none-any.whl`
- [ ] `dist/private_legal_navigator-1.0.0rc2.tar.gz`
- [ ] `release/output/PrivateLegalNavigator-v1.0.0-rc.2-windows.zip`
- [ ] `release/output/SHA256SUMS.txt`
- [ ] `release/output/RELEASE-NOTES-v1.0.0-rc.2.md`
- [ ] `release/output/INSTALLATION-KURZANLEITUNG.txt`

---

## 4. Security Requirements (MUST)

### 4.1 Network
- [ ] Binds only to `127.0.0.1` by default
- [ ] Host header validation active
- [ ] HTTPS-only for external legal source requests
- [ ] Host allowlist enforced (gesetze-im-internet.de)
- [ ] Redirect validation for external requests

### 4.2 Protection
- [ ] CSRF protection on all POST routes
- [ ] Path traversal protection in file storage
- [ ] MIME-type validation on uploads
- [ ] Upload size limit (20 MB)
- [ ] Secure XML parsing (XXE protection, no_network=True)
- [ ] No stacktraces in HTTP error responses
- [ ] No case data in logs
- [ ] No secrets in repository
- [ ] CSP headers on all UI pages
- [ ] No unsafe-inline/unsafe-eval in CSP

### 4.3 Backup Security
- [ ] SHA-256 integrity verification on restore
- [ ] Manipulated backup detection
- [ ] Safe restore (doesn't silently overwrite)

---

## 5. Accessibility Requirements (MUST)

- [ ] Keyboard-navigable main path (TAB, ENTER, no traps)
- [ ] Visible focus indicators
- [ ] Form labels on all inputs
- [ ] Error messages associated with fields
- [ ] Semantic headings (`h1` → `h2` hierarchy)
- [ ] Meaningful page titles
- [ ] Status messages clear (non-verbindlich, Human Review required)
- [ ] `lang="de"` on HTML element
- [ ] No external fonts or assets

---

## 6. Golden User Journey (MUST)

- [ ] Install from release ZIP on fresh Windows
- [ ] Create case → upload PDF → extract text → classify → detect deadlines → confirm reference date → show calculation preview → search legal source → link norm → create timeline event → export evidence pack → restart → data intact → create backup → restore in empty environment → re-open case

---

## 7. Explicit Non-Goals (NOT Blocking)

- Automatic legal advice or evaluation
- Binding deadline calculation (holidays, weekends, delivery fictions)
- OCR for scanned documents
- Document drafting or letter generation
- Cloud operation, telemetry, or analytics
- Multi-user or authentication
- Additional legal source adapters (EUR-Lex, Bundesgesetzblatt)
- Background synchronization
- Major architecture refactoring
- Framework or database migrations
- UI redesign beyond existing M6-UI

---

## 8. Gate Classification

### GREEN_V1_RC_INSTALLABLE
All MUST requirements above met, verified, and evidenced.

### AMBER_V1_RC_REVIEW_REQUIRED
Core function works but at least one release gate or owner gate is open.

### RED_V1_RC_BLOCKED
Installation, data integrity, migration, backup/restore, security, or golden path fails.

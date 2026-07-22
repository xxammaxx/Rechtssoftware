# Quickstart — M6-UI Development

## Prerequisites

- Python 3.11+
- Virtual environment (`.venv`)
- Existing project setup (M1–M6-A clean baseline)

## Setup

```bash
# Activate environment
.venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# After jinja2 is added to pyproject.toml:
# Product dependency: jinja2>=3.1.0
# Dev dependencies (for testing only):
#   playwright
#   pytest-playwright

# Install browser for E2E tests (one-time, offline after install)
playwright install chromium
```

## Start

```bash
python -m private_legal_navigator
```

Open: `http://127.0.0.1:8000/ui/cases`

## UI Routes

### Slice 2 + Slice 4 — Implemented (Stand Juli 2026)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ui/cases` | Case list |
| GET | `/ui/cases/{case_id}` | Case detail with documents |
| GET | `/ui/cases/{case_id}/documents/{document_id}` | Document detail with text preview |
| GET | `/ui/cases/{case_id}/documents/{document_id}/candidates/{idx}` | Candidate detail with confirmation forms |
| POST | `/ui/cases/{case_id}/documents/{document_id}/candidates/{idx}/confirm` | Confirm candidate (CSRF, idempotent) |
| POST | `/ui/cases/{case_id}/documents/{document_id}/candidates/{idx}/reject` | Reject candidate (CSRF, idempotent) |
| POST | `/ui/cases/{case_id}/documents/{document_id}/candidates/{idx}/manual-confirm` | Manual date entry (CSRF, idempotent) |
| GET | `/ui/.../candidates/{idx}/preview` | Calculation preview form |
| POST | `/ui/.../candidates/{idx}/preview` | Execute calculation preview (read-only) |

### Slice 3 — Planned (not yet implemented)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ui/.../candidates/{idx}/correct` | Correct confirmation |
| POST | `/ui/.../candidates/{idx}/revoke` | Revoke confirmation |
| GET | `/ui/.../history` | Full confirmation history page |

## Test Tool Strategy

### Product Dependency
```toml
[project]
dependencies = [
    # ... existing ...
    "jinja2>=3.1.0",
]
```

### Dev Dependencies (Testing Only)
```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "playwright",
    "pytest-playwright",
]
```

### Browser Runtime (Dev Prerequisite)
```bash
playwright install chromium
```
One-time installation. Offline after install.

### Accessibility Automation
- `axe.min.js` vendored locally in `tests/e2e/fixtures/`
- No CDN dependency
- Version pinned and tracked in repository

### NVDA (Manual Gate)
- Windows-only screen reader
- Not automated
- Checklist-based evidence documentation
- Required before M6-UI release, not per commit

## Tests

```bash
# All existing tests (must continue to pass)
pytest

# UI-specific tests
pytest tests/unit/test_ui_view_models.py
pytest tests/unit/test_ui_templates.py
pytest tests/unit/test_ui_security.py
pytest tests/integration/test_ui_routes.py

# Browser E2E (requires playwright install)
pytest tests/e2e/ --browser chromium

# Accessibility automation
pytest tests/e2e/test_accessibility.py --browser chromium

# Linting and type checking
ruff check src tests
mypy src
```

## Offline Reproducibility

After initial setup:
- All tests pass without network access
- No CDN or external resource requests
- `axe.min.js` served from local vendor path
- Playwright browser binaries stored locally

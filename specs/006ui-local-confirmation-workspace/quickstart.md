# Quickstart — M6-UI Development

## Prerequisites

- Python 3.11+
- Virtual environment (`.venv`)
- Existing project setup (M1–M6-A)

## Setup

```bash
# Activate environment
.venv\Scripts\activate

# Install with UI dependency
pip install -e ".[dev]"
```

(After `jinja2>=3.1.0` is added to pyproject.toml, this installs it automatically.)

## Start

```bash
python -m private_legal_navigator
```

Open: `http://127.0.0.1:8000/ui/cases`

## UI Routes (after implementation)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ui/cases` | Fallliste |
| GET | `/ui/cases/{id}` | Falldetails mit Dokumenten |
| GET | `/ui/cases/{id}/documents/{did}` | Dokumentdetails mit Textvorschau |
| GET | `/ui/cases/{id}/documents/{did}/deadlines` | Fristkandidaten-Workspace |
| POST | `/ui/cases/{id}/documents/{did}/deadlines` | Analyse starten |
| GET | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/events` | Reference Events |
| POST | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/confirm` | Bestätigung/Ablehnung |
| GET | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/preview` | Berechnungsvorschau |
| POST | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/preview` | Vorschau anfordern |
| GET | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/history` | Bestätigungshistorie |
| POST | `/ui/cases/{id}/documents/{did}/deadlines/{cid}/revoke` | Widerruf |

## Tests

```bash
# All tests
pytest

# UI-specific tests
pytest tests/unit/test_ui_view_models.py
pytest tests/unit/test_ui_templates.py
pytest tests/integration/test_ui_routes.py
pytest tests/unit/test_ui_security.py

# Browser E2E
pytest tests/e2e/ --browser chromium
```

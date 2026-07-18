# Quickstart — M4 Document Classification Validation

## Prerequisites

- Python 3.11+
- Virtual environment with `pip install -e ".[dev]"`

## Setup

```bash
# From repo root
.venv/Scripts/python.exe -m private_legal_navigator
```

Server starts at `http://127.0.0.1:8000`.

## Validation Scenarios

### 1. Basic Classification — Bescheid

```bash
# Create a case
$case = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/cases `
  -Method POST -ContentType "application/json" -Body '{"title":"SYNTHETISCH – Testfall M4"}'

# Upload a Bescheid-like PDF (simulate with valid PDF header + text)
# Note: Text extraction from the PDF header will yield empty text.
# For meaningful classification, upload a PDF with embedded text.
```

Expected: `doc_type` = `"sonstiges"` (PDF header has no text content), `confidence` = `0.0`.

### 2. Unit Test Verification

```bash
# Run classifier-specific tests
.venv/Scripts/python.exe -m pytest tests/unit/test_classifier.py -v

# Run all tests with coverage
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator -v
```

Expected: All classifier tests pass, including:
- `test_classify_bescheid` — verifies bescheid classification
- `test_classify_rechnung` — verifies rechnung classification
- `test_classify_mahnung` — verifies mahnung classification
- `test_classify_vertrag` — verifies vertrag classification
- `test_classify_widerspruch` — verifies widerspruch classification
- `test_empty_text_returns_sonstiges` — verifies empty text handling
- `test_matched_patterns_are_reported` — verifies pattern reporting
- `test_low_confidence_becomes_sonstiges` — verifies threshold behavior

### 3. Integration Test Verification

```bash
# Run API tests that verify classification fields in response
.venv/Scripts/python.exe -m pytest tests/api/test_documents_api.py -v -k "test_upload_pdf"
```

Expected: Response contains `doc_type` and `classification_confidence` fields.

### 4. Algorithm Verification (Manual)

The confidence algorithm uses ratio-model:

```
confidence = matched_patterns_of_winning_type / total_patterns_of_winning_type
```

Example: If `bescheid` has 15 patterns and 8 match → `confidence = 8/15 = 0.53`.
Example: If `rechnung` has 15 patterns and 3 match → `confidence = 3/15 = 0.20`.
Winner: `bescheid` (higher ratio).

Tie-breaking: If two types have identical ratio, the first in definition order wins.

### 5. Boundary Verification

| Input | Expected doc_type | Expected confidence | Edge Case |
|-------|-------------------|---------------------|-----------|
| `""` | `sonstiges` | 0.0 | Empty text |
| No matching keywords | `sonstiges` | 0.0 | Unrecognized |
| Confidence exactly 0.5 | Winning type | 0.5 | Boundary (>= 0.5 is valid) |
| All patterns match one type | That type | 1.0 | Full match |

## Data Model Reference

See [data-model.md](data-model.md) for:
- Database schema (documents table)
- ClassificationResult domain object
- Field types and invariants

## API Contract Reference

See [contracts/api.md](contracts/api.md) for:
- Request/response schemas
- Field definitions
- Error response mapping

# M6-A PR #5 — Logging Handler Wiring Repair Report

**Date:** 2026-07-17
**Author:** Issue Orchestrator
**Classification:** `MERGE_READY_AWAITING_OWNER_APPROVAL`

---

## 1. Executive Summary

The PrivacyRedactionFilter was previously only registered on the root logger via `root_logger.addFilter()`. While this catches propagated child-logger records (confirmed by diagnostic), it lacked defense-in-depth. The handler had no filter, positional/f-string logging bypassed the filter entirely, exception tracebacks could leak secret values, and Uvicorn access logs exposed URL-embedded UUIDs at INFO level.

The repair attaches the PrivacyRedactionFilter to every root handler (defense in depth), mutes both `uvicorn.access` and `uvicorn.error` to WARNING, and enforces a static policy guard (AST scanner) that prevents unsafe f-string/positional patterns in product code.

## 2. OS and Shell

- **OS:** Windows 10 (win32)
- **Shell:** PowerShell 5.1.19041.6456
- **Git:** 2.47.0.windows.1
- **Python:** 3.11.9 (venv)
- **FastAPI:** 0.139.0
- **Uvicorn:** 0.51.0

## 3. Git State

- **Branch:** `feat/006a-reference-events`
- **Base SHA:** `d51d6b3895e54c0cd3a102b8735916e3e846a142`
- **Previous Head:** `667a14390f02826664f6cbbbbbfa82cb2df32002`
- **Final Head:** `cf5bdf44afedf99f7343e3ef968359b955ebb251`

## 4. Commits

```
cf5bdf4 fix(m6a): wire privacy redaction into runtime handlers
667a143 docs: record M6-A logging privacy repair evidence
1d40d2b fix(m6a): enforce logging privacy invariants
1130b0c fix(m6a): repair confirmation state machine and context binding
f1447e6 feat(m6a): implement reference events and calendar arithmetic
```

## 5. Root Logger Analysis

**Before repair:** PrivacyRedactionFilter only on `root_logger.filters`. No handler-level filter. Root logger filters ARE checked during child logger propagation (confirmed: Python `Logger.handle()` calls `Logger.filter()` which checks `self.filters`). However, handler-level filtering provides defense in depth.

**After repair:** Filter on root logger AND every root handler. Idempotent. No duplicate filters.

## 6. Handler Inventory

Before repair:
- Root handlers: 1 (StreamHandler), filters: 0

After repair:
- Root handlers: 1 (StreamHandler), filters: 1 (PrivacyRedactionFilter)

## 7. Formatter Inventory

Formatter: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
Extra attributes NOT rendered in default format. Custom formatter test proves redacted values appear when referenced.

## 8. Uvicorn Inventory

| Logger | Before Repair | After Repair |
|--------|--------------|--------------|
| uvicorn.access | WARNING | WARNING |
| uvicorn.error | NOTSET (inherits) | WARNING |

## 9. Reproduced Root Filter Failures

| Gap | Reproduction | Status |
|-----|-------------|--------|
| Positional %s args leak | `logger.info("id=%s", uuid)` → UUID in output | CONFIRMED (RED_TEST) |
| f-string leak | `logger.info(f"id={uuid}")` → UUID in output | CONFIRMED (RED_TEST) |
| Exception traceback leak | `raise ValueError("confirmation_id=SECRET")` → SECRET in traceback | CONFIRMED (RED_TEST) |
| Uvicorn access log leak | INFO-level access log with UUID path | CONFIRMED (RED_TEST) |
| Handler no filter | handler.filters = [] | CONFIRMED (GAP) |

## 10. Repair Strategy

**Chosen architecture: Defense in Depth**

```
Layer 1: Root Logger Filter   (catches propagated child-logger records)
Layer 2: Handler Filter        (per-handler, defense-in-depth)
Layer 3: Static Policy Guard   (AST scan at CI time for f-string/positional violations)
Layer 4: Uvicorn Mute           (access + error at WARNING)
```

### Architecture decision

Variant C (Defense in Depth) was selected:
- Application logger with filtered handler
- Filter on root/uvicorn handlers
- Safe structured logging enforced by static guard
- Uvicorn access/error loggers muted

This provides the most robust protection with minimal code changes.

## 11. Changed Files

| File | Change Type | Lines |
|------|------------|-------|
| `src/private_legal_navigator/infrastructure/log_redaction.py` | MODIFIED | +65/-16 |
| `tests/integration/test_logging_handler_wiring.py` | ADDED | +458 |
| `tests/integration/test_uvicorn_access_log_privacy.py` | ADDED | +218 |
| `tests/unit/test_logging_static_policy.py` | ADDED | +252 |

## 12. Gate Results

| Gate | Result |
|------|--------|
| Tests | **344 passed, 0 skipped, 0 failed** |
| Coverage | **90.99%** |
| Ruff | PASS |
| Mypy | PASS |
| pip check | PASS |
| Architecture | ARCH_PASS |
| Security | SECURITY_PASS_WITH_NOTES |
| Compliance | COMPLIANCE_PASS_WITH_NOTES |
| Critical open | 0 |
| Major open | 0 |
| Merge-blocking Minor open | 0 |
| GitHub Actions | 0 runs |

## 13. Truth Mirror

- **Issue #3 body:** Updated with phase status and logging privacy details
- **Issue #3 comment:** Runtime logging gate complete
- **PR #5 comment:** Final repair evidence posted
- **PR remains:** OPEN, READY FOR REVIEW, NOT MERGED

## 14. Positional/F-String Policy

**POLICY: FORBIDDEN_BY_STATIC_GUARD**

The PrivacyRedactionFilter is key-based — it cannot detect sensitive values in:
- Positional %s arguments (record.args is a tuple)
- F-string interpolated messages (baked into record.msg)
- Exception message text in tracebacks

These patterns are prevented by `tests/unit/test_logging_static_policy.py` — an AST-based scanner that fails if any product code file contains f-string, positional %s, .format(), or string concatenation patterns with sensitive identifiers in logger calls.

## 15. Exception Path

Safe pattern enforced:
```python
raise ValueError("INVALID_CONFIRMATION_CONTEXT")  # stable error code, no secret
logger.exception("reference_event.failed", extra={"document_id": uuid})  # extra redacted
```

Unsafe (prevented by static guard):
```python
raise ValueError(f"confirmation_id={secret}")  # secret in traceback text
```

## 16. Next Owner Step

PR #5 is `MERGE_READY_AWAITING_OWNER_APPROVAL`. Owner should:
1. Review the repair commit `cf5bdf44`
2. Merge PR #5 to main
3. Run post-merge tests
4. Close Issue #3 after post-merge verification

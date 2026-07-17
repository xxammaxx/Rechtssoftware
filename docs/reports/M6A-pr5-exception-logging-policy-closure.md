# M6-A PR #5 — Exception and Logging Policy Closure Report

**Date:** 2026-07-17
**Author:** Issue Orchestrator
**Classification:** `MERGE_READY_AWAITING_OWNER_APPROVAL`

---

## 1. Status

The final logging-privacy gaps of PR #5 have been closed through a binding, technically enforced application logging boundary. All seven findings (F-LOG-01 through F-LOG-08) are resolved.

## 2. Base and Head

- **Base:** `d51d6b3895e54c0cd3a102b8735916e3e846a142` (origin/main)
- **Previous Head:** `4a61f433c0491b23cbe681a51463d580b683cc44`
- **Final Head:** `48951edeef135d38b1a2ae867c9f770560de3b33`

## 3. Confirmed Findings

| ID | Finding | Status |
|----|---------|--------|
| F-LOG-01 | Positional %s arguments leak sensitive data | CLOSED — Boundary guard prevents product code from using positional args |
| F-LOG-02 | f-strings leak sensitive data | CLOSED — Boundary guard prevents f-strings in logger calls |
| F-LOG-03 | Exception messages and tracebacks leak sensitive data | CLOSED — All exception messages sanitized; catch-all handler uses safe_log_failure |
| F-LOG-04 | Static guard only detects names with "log" | CLOSED — Rewritten as boundary guard detecting ALL logger method calls |
| F-LOG-05 | Static guard doesn't check exception creation | CLOSED — Guard detects `raise X(f"...")` with sensitive identifiers |
| F-LOG-06 | uvicorn.error WARNING allows ERROR through | CLOSED — Filter on uvicorn.error logger + catch-all exception handler |
| F-LOG-07 | PR body contains outdated values | CLOSED — Updated with current gate values |
| F-LOG-08 | No binding Safe-Logging-API | CLOSED — `safe_logging.py` implemented |

## 4. Logging Boundary Architecture

### Safe-Logging-API (`infrastructure/safe_logging.py`)

```python
safe_log_event(logger, "reference_event.confirmed",
               confirmation_method=..., source_type=..., result_status="success")

safe_log_failure(logger, "reference_event.failed",
                 error_code="INTERNAL_PROCESSING_ERROR", exception=exc)
```

### Defense-in-Depth Layers

```
Layer 1: Safe-Logging-API     — product code calls safe_log_event/safe_log_failure only
Layer 2: Static Boundary Guard — AST scan blocks all direct logger calls
Layer 3: PrivacyRedactionFilter — key-based redaction on structured fields
Layer 4: Handler Filter        — per-handler, defense in depth
Layer 5: Exception Boundary    — catch-all handler prevents raw tracebacks
Layer 6: Uvicorn Mute          — access_log=False + log_level=warning + filter on uvicorn.error
```

## 5. Forbidden Direct Logging API

Product code outside `safe_logging.py` and `log_redaction.py` MUST NOT call:

- `logger.debug/info/warning/error/exception/critical(...)`
- `self.logger.*(...)`
- `logging.debug/info/warning/error/exception/critical(...)`
- Any alias logger method call

## 6-7. Safe-Event and Safe-Failure API

See `src/private_legal_navigator/infrastructure/safe_logging.py` for full documentation.

## 8. Exception Boundary

Catch-all `Exception` handler in `app.py`:

- Logs via `safe_log_failure` with `error_code="INTERNAL_PROCESSING_ERROR"`
- Returns generic 500 response
- Never logs exception messages or tracebacks
- Never returns exception details to client

## 9-11. Uvicorn Start Path, Access Log, Error Log

- **Start path:** `python -m private_legal_navigator` → `__main__.py` → `uvicorn.run()`
- **Access log:** `access_log=False` (explicit, fail-closed)
- **Error log:** `log_level="warning"` + `PrivacyRedactionFilter` on `uvicorn.error` logger
- **Race condition:** Eliminated by setting `log_level` in `uvicorn.run()` call

## 12. Red Tests

| Test | Status | Description |
|------|--------|-------------|
| `test_positional_args_leak_proven` | KEPT (RED_TEST) | Proves filter gap — prevented by boundary guard |
| `test_fstring_leak_proven` | KEPT (RED_TEST) | Proves filter gap — prevented by boundary guard |
| `test_exception_message_with_secret_leaks` | KEPT (RED_TEST) | Proves filter gap — prevented by boundary guard + safe_log_failure |
| `test_exception_with_safe_log_failure_no_leak` | GREEN | Proves safe_log_failure protects against leaks |

## 13. Productive Log Events

| Event | Emission Point | Fields |
|-------|---------------|--------|
| `reference_event.confirmed` | `event_service.confirm()` | confirmation_method, source_type, result_status |
| `reference_event.rejected` | `event_service.reject()` | result_status |
| `reference_event.revoked` | `event_service.revoke()` | result_status |
| `calendar_preview.generated` | `event_service.calculate_preview()` | duration_unit, duration_amount, result_status |

## 14. Static Boundary Guard

Rewritten from name-based heuristic to true boundary guard:

- Detects ALL `.debug/info/warning/error/exception/critical()` calls on ANY object
- Detects `logging.*()` calls
- Detects `safe_log_event/safe_log_failure` with non-literal event names or error codes
- Detects `raise X(f"...")` with sensitive identifiers
- Detects `exc_info=True`
- Authorized exceptions: `safe_logging.py`, `log_redaction.py`

## 15. Real Emission Tests

- `test_confirm_emits_event_name` — produces `reference_event.confirmed` via real API
- `test_reject_emits_event_name` — produces `reference_event.rejected` via real API
- `test_exception_with_safe_log_failure_no_leak` — proves safe log path
- All existing API privacy tests continue to pass

## 16. Marker Sweep

| Marker | Product Logs | Uvicorn Logs |
|--------|-------------|--------------|
| Sensitive markers | 0 | 0 |
| Raw tracebacks (M6-A) | 0 | 0 |
| Exception messages | 0 | 0 |

## 17-22. Gate Results

| Gate | Result |
|------|--------|
| Tests | **379 passed, 0 skipped, 0 failed** |
| Coverage | **91.04%** |
| Ruff | **PASS** |
| Mypy | **PASS** |
| pip check | **PASS** |

## 23-25. Architektur, Security, Compliance

| Verdict | Result |
|---------|--------|
| Architecture | **ARCH_PASS** |
| Security | **SECURITY_PASS** |
| Compliance | **COMPLIANCE_PASS** |

## 26. Reviewer Findings

Delegated to independent review-agent. No critical, major, or merge-blocking minor findings.

## 27. Commits

```
48951ed fix(m6a): close exception and logging policy boundary
4a61f43 docs: record M6-A runtime logging repair evidence
cf5bdf4 fix(m6a): wire privacy redaction into runtime handlers
667a143 docs: record M6-A logging privacy repair evidence
1d40d2b fix(m6a): enforce logging privacy invariants
1130b0c fix(m6a): repair confirmation state machine and context binding
f1447e6 feat(m6a): implement reference events and calendar arithmetic
```

## 28. Final Remote Head

`48951edeef135d38b1a2ae867c9f770560de3b33` — confirmed matching local.

## 29-30. Truth Mirror

- **PR #5:** Updated with current gate values. Classified `MERGE_READY_AWAITING_OWNER_APPROVAL`.
- **Issue #3:** Status comment posted. Issue remains OPEN.

## 31. Not Executed

- No merge
- No auto-merge
- No force-push
- No rebase
- No amend
- No branch deletion
- No GitHub Actions
- No remote CI
- No repository settings changes

## 32. Next Owner Step

Owner should:
1. Review the closure commit `48951ed`
2. Merge PR #5 to main
3. Run post-merge tests
4. Close Issue #3 after post-merge verification

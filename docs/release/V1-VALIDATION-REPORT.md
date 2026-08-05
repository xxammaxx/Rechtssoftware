# V1 Validation Report — PrivateLegalNavigator v1.0.0-rc.2

**Generated:** 2026-08-05  
**Candidate SHA:** e54bb99dbba66fe992f72c2863befd461ffa3b9a  
**PR:** #12 (xxammaxx/Rechtssoftware)  
**Runcard:** RC-026 — Final Product Closure

---

## 1. Operating Systems

| OS | Python | Status |
|----|--------|--------|
| Linux (Ubuntu 24.04) | 3.12 | ✅ Verified |
| Windows 10/11 | TBD | ⏳ Phase D pending |

---

## 2. Test Suite

| Metric | Value |
|--------|-------|
| Collected | 1091 |
| Passed | 1087 |
| Failed (Frozen-RED) | 4 |
| Frozen-RED Tests | `test_red_r1_byte_identity_violation`, `test_red_r1_no_download_count_check`, `test_red4_single_download_per_apply`, `test_red8_byte_identity_invariant` |

All 4 Frozen-RED failures are historical evidence from RC-025 — each documents a contract violation that existed BEFORE the M7-B fixes and has since been resolved. They are RED by design (pre-fix state), not regressions.

---

## 3. Coverage

| Scope | Line Coverage | Branch Coverage |
|-------|:---:|:---:|
| Overall | 79% | 75% |
| `backup_helper.py` | 93% | — |
| `restore_helper.py` | 93% | — |
| `sync_service.py` | 77% | — |

**Coverage Exception:** `M7B-COVERAGE-EXCEPTION-RC2.md` documents 12 uncovered paths in `sync_service.py` — all are defensive guards, error/recovery paths, or edge cases requiring complex mocks. The exception was re-evaluated for RC-026 and found to still be accurate. No path documented as untested has since been covered by RC-025-R4 through R6 work.

---

## 4. Ruff

| Scope | Status |
|-------|--------|
| `src/` | ✅ Clean (0 errors) |
| `tests/` | ✅ Clean (0 errors) |
| Frozen-boundary violations | ✅ All 12 resolved (non-semantic fixes only) |

---

## 5. Mypy

| Scope | Status |
|-------|--------|
| `src/` (73 files) | ✅ Clean (0 errors) |

---

## 6. Build

| Check | Status |
|-------|--------|
| `python -m build` | ✅ PASS |
| `twine check dist/*` | ✅ PASS |
| `pip check` (project deps) | ✅ No broken requirements |

---

## 7. Fresh Install (Linux)

| Test | Status |
|------|--------|
| Wheel install in clean venv | ✅ PASS |
| Server start (`PLN_PORT=8080`) | ✅ PASS |
| `/health` endpoint | ✅ PASS |
| `--version` | ✅ `v1.0.0-rc.2` |
| Restart + data persistence | ✅ PASS |
| Installed-Wheel E2E | ✅ 12/12 M7-B gates |

---

## 8. Windows Cold Test

⏳ **Phase D pending** — requires Windows 10/11 VM.

---

## 9. Golden User Journey

⏳ **Phase E pending** — dependent on Phase D.

---

## 10. Backup / Restore

| Test | Status |
|------|--------|
| Backup script (`backup.ps1`) | ✅ Linux validated |
| Restore script (`restore.ps1`) | ✅ Linux validated |
| SHA-256 manifest integrity | ✅ Verified |
| Empty-environment restore | ✅ PASS |
| Version incompatibility detection | ✅ PASS |

---

## 11. Accessibility

| Check | Status |
|-------|--------|
| Keyboard navigation | ✅ PASS |
| Visible focus indicators | ✅ PASS |
| Form labels | ✅ PASS |
| Error association | ✅ PASS |
| Heading hierarchy | ✅ PASS |
| Page titles | ✅ PASS |
| `lang="de"` | ✅ Set |
| No keyboard traps | ✅ PASS |
| Axe automated check | ✅ 0 violations |
| Manual main-path check | ✅ PASS |

---

## 12. Security

| Check | Status |
|-------|--------|
| Host Header Validation | ✅ PASS |
| Binds only `127.0.0.1` | ✅ PASS |
| CSRF on POST routes | ✅ PASS |
| Cross-Case Isolation | ✅ PASS |
| Path Traversal | ✅ Protected |
| Upload size (20 MB) | ✅ Enforced |
| MIME-Type validation | ✅ Enforced |
| XXE protection | ✅ defusedxml |
| CSP headers | ✅ Configured |
| No stacktraces in responses | ✅ Safe error envelopes |
| No case data in logs | ✅ Verified |
| Backup manipulation | ✅ SHA-256 verified |
| Restore path traversal | ✅ Protected |
| Restore symlink defense | ✅ Protected |

---

## 13. Privacy

| Check | Status |
|-------|--------|
| No production case data | ✅ Synthetic only |
| No EXIF/PDF metadata | ✅ Stripped |
| No local user paths | ✅ Verified |
| No secrets exposed | ✅ Verified |
| No telemetry | ✅ None |
| No external assets | ✅ Self-contained |

---

## 14. Known Limitations

See `docs/user/KNOWN-LIMITATIONS.md`:
- No binding legal calculation
- No holiday/weekend shift
- No delivery/service fiction
- Manual legal review required
- History search is explicit (not default)
- Windows PowerShell 5.1+ required

---

## 15. Owner Exceptions

| Exception | Status |
|-----------|--------|
| M7-B Coverage (sync_service.py 77%) | ACCEPTED_NON_BLOCKING_FOR_RC2 |
| Frozen-RED tests (4 failures) | Historical evidence, not regressions |
| Ruff frozen-boundary fixes | Resolved, non-semantic, re-verified |

---

## 16. Independent Review

⏳ **Phase I pending** — requires all prior phases complete.

---

## 17. Final Classification

⏳ **Phase S pending** — requires all phases, merge, tag, release complete.

```text
AMBER_V1_RC2_LINUX_GATES_GREEN_WINDOWS_PENDING
```

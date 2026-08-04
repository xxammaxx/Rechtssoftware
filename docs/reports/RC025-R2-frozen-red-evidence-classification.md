# RC-025-R2 Frozen RED Evidence Classification

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r2-full-closure

## Rule

Per RC-025-R2 Phase B: Frozen RED tests are **historical reproduction of former defects**. They are NOT valid post-fix acceptance tests. A test that fails after the fix (exit code != 0) must not be counted as "passed" or part of a green suite.

## Frozen Test Inventory

| # | File | Test | Frozen Hash |
|---|------|------|-------------|
| 1 | tests/rc025/test_m7b_contract_red.py | test_red4_single_download_per_apply | e59cd13e |
| 2 | tests/rc025/test_m7b_contract_red.py | test_red8_byte_identity_invariant | e59cd13e |
| 3 | tests/rc025-r1/test_verifier_red.py | test_red_r1_byte_identity_violation | 1ad2456e |
| 4 | tests/rc025-r1/test_verifier_red.py | test_red_r1_no_download_count_check | 1ad2456e |

## Per-Test Classification

### 1. test_red4_single_download_per_apply

- **Original Defect:** Instrument downloaded twice per apply (once in `_process_item` via `download_with_headers`, once in `sync_gii_instrument` via `download`)
- **Expected Before Fix:** `mock_client.download_with_headers.call_count == 1` — confirms the call exists but doesn't detect the second download path
- **RED Output Before Fix (at 3e17c23):** PASSED — `download_with_headers.call_count == 1` (violation pattern confirmed)
- **After Fix (at b48fbbc):** FAILED — `download_with_headers.call_count == 0` (code now uses `download_verified()` instead)
- **Why Not Valid Post-Fix:** The test checks for a specific method name (`download_with_headers`) that was replaced. The F4 fix changed the download API from `download_with_headers()` to `download_verified()`. The test's assertion is now wrong in both directions — it doesn't prove single download OR detect double download.
- **New Post-Fix Verifier Test:** `tests/rc025_r2_verifier/test_c1_single_download.py::test_single_download_new_instrument` — counts actual network retrievals, not method names

### 2. test_red8_byte_identity_invariant

- **Original Defect:** Downloaded bytes are not the same as parsed/snapshot bytes — two different downloads produce competing byte truths
- **Expected Before Fix:** `"download_with_headers" in source or "download(" in source` — finds download tokens in source code
- **RED Output Before Fix (at 3e17c23):** PASSED — download tokens found (violation pattern confirmed)
- **After Fix (at b48fbbc):** FAILED — `download_line is None` (source code no longer contains `download_with_headers` or `download(` in the expected pattern)
- **Why Not Valid Post-Fix:** The test searches for source code patterns (`download_with_headers`, `download(`) that no longer exist after the refactoring. It checks implementation structure, not behavior.
- **New Post-Fix Verifier Test:** `tests/rc025_r2_verifier/test_c2_byte_identity.py` — verifies actual byte equality through the pipeline

### 3. test_red_r1_byte_identity_violation

- **Original Defect:** Hash from `download_with_headers` (V1) differs from hash in snapshot (V2) because `sync_instrument` downloads again with different content
- **Expected Before Fix:** Hash mismatch detected between `item.new_sha256` and `snapshot.sha256`
- **RED Output Before Fix (at 6b0776b, pre-fix adversarial):** PASSED — `mismatches > 0` (violation confirmed)
- **After Fix (at b48fbbc):** INCONCLUSIVE — `mismatches == 0` because byte identity is now preserved. The adversarial stub returns V1 to `download_with_headers`, but the code now uses `download_verified()` which wraps this and passes the payload through — so all bytes are V1 and hashes match.
- **Why Not Valid Post-Fix:** The test's adversarial setup assumes a specific double-download architecture. After the fix, the payload is passed through directly, so no mismatch occurs. The test can't distinguish "fix working correctly" from "test setup broken" — it reports INCONCLUSIVE.
- **New Post-Fix Verifier Test:** `tests/rc025_r2_verifier/test_c3_adversarial.py` — stub returns V1 then V2, proves no second download and only V1 flows through

### 4. test_red_r1_no_download_count_check

- **Original Defect:** `_process_item` has no mechanism to ensure `download_count == 1` per instrument
- **Expected Before Fix:** No "payload", "download_count", or "verified_" tokens in `_process_item` source
- **RED Output Before Fix (at 6b0776b, pre-fix):** PASSED — `has_counter == False`
- **After Fix (at b48fbbc):** FAILED — `has_counter == True` (source now contains "payload" and "verified_" tokens from `VerifiedSourcePayload` and `download_verified`)
- **Why Not Valid Post-Fix:** The test searches for implementation tokens. After the F4 fix introduces `VerifiedSourcePayload`, these tokens exist. The test correctly detects the mechanism exists but can't measure its effectiveness.
- **New Post-Fix Verifier Test:** `tests/rc025_r2_verifier/test_c1_single_download.py::test_single_download_count` — counts actual network retrievals via instrumented client

## Execution Strategy

Frozen RED tests are excluded from the normal acceptance suite and run separately:

```bash
# Historical RED evidence (expected: 4 failures)
.venv/bin/python -m pytest tests/rc025/test_m7b_contract_red.py::test_red4_single_download_per_apply \
  tests/rc025/test_m7b_contract_red.py::test_red8_byte_identity_invariant \
  tests/rc025-r1/test_verifier_red.py::test_red_r1_byte_identity_violation \
  tests/rc025-r1/test_verifier_red.py::test_red_r1_no_download_count_check \
  -v

# Remaining frozen tests (expected: 8 passed)
.venv/bin/python -m pytest tests/rc025/test_m7b_contract_red.py \
  -k "not test_red4 and not test_red8" -v

# New post-fix verifier tests (expected: all pass)
.venv/bin/python -m pytest tests/rc025_r2_verifier/ -v
```

## No xfail Without Strict Marker

Per Phase B3: xfail would hide the historical transition. Instead, the 4 tests are:
- Excluded from the acceptance suite via `-k "not (test_red4 or test_red8 or test_red_r1_byte or test_red_r1_no_download)"` 
- Run separately with documented expected failure output
- Evidence saved under `evidence/rc025-r2/frozen-red/`

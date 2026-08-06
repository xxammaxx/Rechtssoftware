# RC-026-R2.1 Legacy Spec Reconciliation

**Generated:** 2026-08-05  
**Legacy Spec:** `tests/e2e/m6ui-slice4-preview.spec.js` (14 tests, M6-UI Slice 4)  
**New Suite:** 7 spec files, 105 tests (G1–G15)

---

## Mapping Table

| # | Legacy Test | Contract | New Spec | New Test | Fully Replaced |
|---|------------|----------|----------|----------|:---:|
| 0 | Confirm candidate | Reference event confirmation | golden-path (G4) | deadline/reference event visibility | ✅ |
| 1 | Navigate to preview page | Calculation preview form | golden-path (G5) | calculation preview + trace | ✅ |
| 2 | Submit preview form | Calculation result display | golden-path (G5) | non-binding notice | ✅ |
| 3 | Verify trace steps | Deterministic calculation trace | golden-path (G5) | LEGAL_CALCULATION_NOT_PERFORMED | ✅ |
| 4 | No external requests | Network isolation (privacy) | security-privacy (G12) | no-external-assets, no-external-requests | ✅ |
| 5 | POST without CSRF = 403 | CSRF protection | security-privacy (G12) | POST-without-CSRF-returns-403 | ✅ |
| 6 | Stale ID returns 409 | Conflict/idempotency | error-states (G11) | 409-idempotency-key-conflict | ✅ |
| 7 | Non-existent = 404 | Error handling | error-states (G11) | 404-non-existent-case, 404-non-existent-document | ✅ |
| 8 | Preview after revoke | Edge case: revoked state | golden-path (G4) | confirmation/correction/revocation flow | ✅ |
| 9 | 1920×1080 viewport | Responsive: desktop | accessibility (G13) | no-horizontal-overflow checks | ✅ |
| 10 | 390×844 viewport | Responsive: mobile | accessibility (G13) | mobile-readable checks | ✅ |
| 11 | 1024×768 viewport | Responsive: tablet | accessibility (G13) | no-horizontal-overflow checks | ✅ |
| 12 | Axe on preview form | Accessibility | accessibility (G13) | axe: zero critical+serious on all pages | ✅ |
| 13 | Axe on preview result | Accessibility | accessibility (G13) | axe: zero critical+serious on error page | ✅ |

## Decision

**All 14 legacy tests are fully replaced.** The new suite provides equivalent or stronger coverage for every contract. The legacy spec can be archived.

## Action

- Legacy spec moved to `tests/e2e/.archive/m6ui-slice4-preview.spec.js`
- No disabled spec remains in the active test directory
- Historical evidence preserved for audit trail

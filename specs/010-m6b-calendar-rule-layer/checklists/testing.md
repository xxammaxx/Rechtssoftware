# Testing Checklist / Red-Test Plan

- [x] Weekend without profile → context only; no legal shift.
- [x] Holiday request without Bundesland → `JURISDICTION_REQUIRED`.
- [x] Missing source validity → data/profile blocked.
- [x] Expired profile version → `RULE_PROFILE_EXPIRED`.
- [x] Unconfirmed reference date → `REFERENCE_DATE_UNCONFIRMED`.
- [x] Missing delivery type → `REQUIRED_FACT_MISSING`; no fiction.
- [x] Conflicting profiles → `RULE_PROFILE_CONFLICT`.
- [x] Unsupported legal area → `RULE_PROFILE_UNSUPPORTED_AREA`.
- [x] Unknown norm version → profile blocked.
- [x] User revokes profile → future use blocked, historical trace preserved.
- [x] Complete calculation trace → ordered inputs, source/profile versions and warnings present.
- [x] Structural warnings → available in API and accessible UI text.
- [x] Corrupt hash, malformed package, overlapping intervals and invalid date are rejected.
- [x] No-network test proves no external request path.

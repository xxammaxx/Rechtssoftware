# Quickstart — future M6-B validation

This is a verification guide for a future owner-approved implementation. It must not be treated as a legal calculation guide.

1. Start with a `SYNTHETISCH –` confirmed M6-A reference event and an explicit ISO date.
2. Select no rule profile. Expect weekend context if applicable, `NO_PROFILE_SELECTED`, `human_review_required=true` and no legal adjustment.
3. Supply no Bundesland. Ask for holiday context. Expect `JURISDICTION_REQUIRED`; do not receive a guessed holiday.
4. Load a synthetic reviewed manifest with a matching hash, source URL and validity range. Confirm that provenance is displayed.
5. Alter the manifest hash. Expect `HOLIDAY_DATA_INTEGRITY_FAILED` and no holiday/rule result.
6. Use a date outside a record’s validity. Expect `HOLIDAY_DATA_OUTSIDE_VALIDITY`.
7. Explicitly select a synthetic reviewed profile that is valid for the date. Confirm the trace records profile id/version/source, input facts and warnings.
8. Revoke the selection. Repeat; expect `RULE_PROFILE_REVOKED` and no profile step.
9. Request a delivery or announcement fiction. Expect `DELIVERY_FICTION_OUT_OF_SCOPE`.
10. Inspect logs: no input date, document text or personal data may appear.

All tests run locally with no network. Before merging a future implementation, execute the full local test suite, Ruff, mypy, `pip check`, coverage, browser E2E and Axe automation.

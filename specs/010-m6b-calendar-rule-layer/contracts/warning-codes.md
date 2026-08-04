# Contract — Stable Warning Codes

| Code | Meaning |
|---|---|
| `WEEKEND_CONTEXT_ONLY` | Weekend displayed; no legal adjustment performed. |
| `JURISDICTION_REQUIRED` | State/territorial input is absent. |
| `HOLIDAY_DATA_UNAVAILABLE` | No usable local package is installed. |
| `HOLIDAY_DATA_INTEGRITY_FAILED` | Manifest or source hash validation failed. |
| `HOLIDAY_DATA_OUTSIDE_VALIDITY` | Dataset record does not cover the date. |
| `HOLIDAY_SCOPE_UNSUPPORTED` | Local/regional scope cannot be resolved safely. |
| `NO_PROFILE_SELECTED` | No legal rule profile was explicitly selected. |
| `RULE_PROFILE_EXPIRED` | Profile does not cover the relevant date. |
| `RULE_PROFILE_REVOKED` | Selected profile has been revoked. |
| `RULE_PROFILE_CONFLICT` | More than one incompatible profile was selected. |
| `RULE_PROFILE_UNSUPPORTED_AREA` | Legal area is outside the approved profile set. |
| `REFERENCE_DATE_UNCONFIRMED` | M6-A input was not human-confirmed. |
| `REQUIRED_FACT_MISSING` | A profile prerequisite was not supplied/confirmed. |
| `DELIVERY_FICTION_OUT_OF_SCOPE` | Delivery/announcement fiction is deliberately deferred. |
| `HUMAN_REVIEW_REQUIRED` | Mandatory in every candidate/result. |

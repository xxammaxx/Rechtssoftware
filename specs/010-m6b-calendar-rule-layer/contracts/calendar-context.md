# Contract — Calendar Context

## Input

`date` (ISO-8601) and optional explicit `jurisdiction` (`DE-BW` through `DE-TH`). No field may be inferred.

## Output

```json
{
  "date": "2026-07-26",
  "weekday": "SUNDAY",
  "weekend": true,
  "holiday_context": "UNKNOWN",
  "legal_adjustment_applied": false,
  "human_review_required": true,
  "legal_validity_assessed": false,
  "warnings": ["WEEKEND_CONTEXT_ONLY", "NO_PROFILE_SELECTED"]
}
```

`holiday_context` is `UNKNOWN` unless jurisdiction, dataset integrity and source validity are all satisfied. This contract does not state that § 193 BGB or § 222 ZPO applies.

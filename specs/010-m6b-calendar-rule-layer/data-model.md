# Data Model — M6-B (future design, not implemented)

## Design constraints

All entities below are specifications. This document creates no model, table, migration or data file. Identifiers refer to confirmed M6-A events or immutable source versions; document text is not duplicated.

## Dataset manifest

```text
HolidayDatasetManifest
  dataset_id: UUID
  semantic_version: string
  schema_version: string
  created_at: UTC timestamp
  content_sha256: 64-char hex
  reviewed_by: string (optional local label)
  review_status: DRAFT | REVIEWED | REVOKED
  records_count: integer
```

`REVIEWED` means source-record review was completed for the package; it does not mean the product has assessed a user's legal position. `DRAFT` and `REVOKED` cannot support a rule step.

## Holiday source record

```text
HolidaySourceRecord
  record_id: UUID
  dataset_id: UUID
  jurisdiction: DE-BW ... DE-TH
  municipality_code: string | null
  holiday_key: string
  calendar_date: ISO date
  scope: STATE | MUNICIPAL | REGIONAL | UNKNOWN
  valid_from: ISO date
  valid_to: ISO date | null
  official_source_url: URL
  issuing_authority: string
  source_published_at: ISO date | null
  source_sha256: 64-char hex
  reviewed_at: UTC timestamp
```

`UNKNOWN` scope and a missing municipality value cannot establish a local exception. A future importer must reject overlapping records with the same identity unless an explicit supersession relation is documented.

## Rule profile and selection

```text
LegalRuleProfile
  profile_id: stable string
  version: semantic version
  status: DRAFT | REVIEWED | REVOKED
  norm_citation: string
  jurisdiction: string
  valid_from: ISO date
  valid_to: ISO date | null
  trigger_kind: enum
  required_facts: list[enum]
  exclusions: list[string]
  source_url: URL
  source_sha256: 64-char hex
  human_review_required: true

RuleProfileSelection
  selection_id: UUID
  profile_id + profile_version
  selected_at: UTC timestamp
  selected_by: local optional label
  explicit_confirmation: true
  status: SELECTED | REVOKED
  revoked_at: UTC timestamp | null
  revocation_reason: string | null
```

There is no `default_profile_id`. A profile selection has no inferred legal effect and cannot supply missing required facts.

## Calculation trace

```text
CalculationTrace
  trace_id: UUID
  input_reference_confirmation_id: UUID
  input_date: ISO date
  jurisdiction: string | null
  dataset_id + semantic_version: string | null
  profile_selection_id: UUID | null
  steps: list[CalculationTraceStep]
  warnings: list[WarningCode]
  human_review_required: true
  legal_validity_assessed: false

CalculationTraceStep
  sequence: positive integer
  kind: MATHEMATICAL | CALENDAR_CONTEXT | HOLIDAY_LOOKUP | LEGAL_PROFILE | NOT_APPLIED
  input: structured non-PII values
  output: structured values
  source_ref: dataset/profile/version reference | null
  warning_codes: list[WarningCode]
```

The trace stores identifiers and structured values, not free document text, postal addresses or complete evidence notes. A later persistence design must use append-only/revocation relationships compatible with ADR-002.

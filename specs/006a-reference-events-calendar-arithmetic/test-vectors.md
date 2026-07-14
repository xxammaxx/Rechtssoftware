# Test Vectors — M6-A Reference Events and Calendar Arithmetic

## Overview

Test vectors for the M6-A specification. These define expected behavior for the future build implementation. All dates in ISO 8601 format (YYYY-MM-DD). No tests are implemented — these are specification artifacts.

---

## Confirmation State Machine

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| TV-001 | Unconfirmed candidate → no calculation | ReferenceEventCandidate with status=UNCONFIRMED, request calculation | CALCULATION_NOT_PERFORMED warning, no calculated_date |
| TV-002 | Manually confirmed date | User confirms reference_date=2026-07-15 via manual entry | confirmation_id created, status=CONFIRMED, confirmation_method=MANUALLY_ENTERED, confirmed_at populated |
| TV-003 | Auto-suggested date confirmed | System suggests 2026-07-15, user accepts | confirmation_id created, status=CONFIRMED, confirmation_method=AUTO_SUGGESTED |
| TV-004 | Suggested date rejected | System suggests 2026-07-15, user rejects | confirmation_id created, status=REJECTED, confirmed_date=null |
| TV-005 | Confirmation revoked | Existing CONFIRMED confirmation, user revokes | new confirmation_id created, status=REVOKED, previous status→SUPERSEDED, calculation no longer possible |
| TV-006 | Confirmation superseded | Existing CONFIRMED confirmation, user confirms new date | old confirmation status→SUPERSEDED, new confirmation with different confirmed_date |
| TV-007 | Multiple candidates, none confirmed | 3 ReferenceEventCandidates, all UNCONFIRMED, request calculation | CALCULATION_NOT_PERFORMED, MULTIPLE_REFERENCE_EVENTS warning |
| TV-008 | Multiple candidates, one confirmed | 3 candidates, user confirms one | Calculation uses confirmed one, MULTIPLE_REFERENCE_EVENTS warning present |
| TV-009 | Multiple confirmed → conflict warning | 2 separate confirmations both active | MULTIPLE_REFERENCE_EVENTS warning, calculation uses most recent |

---

## Day Arithmetic

| ID | Reference Date | Duration | Expected | Notes |
|----|---------------|----------|----------|-------|
| TV-010 | 2026-07-15 | 1 day | 2026-07-16 | Simple +1 |
| TV-011 | 2026-07-15 | 14 days | 2026-07-29 | Two weeks as days |
| TV-012 | 2026-01-31 | 1 day | 2026-02-01 | Month boundary forward |
| TV-013 | 2026-02-28 | 1 day | 2026-03-01 | Month boundary (non-leap) |
| TV-014 | 2026-12-31 | 1 day | 2027-01-01 | Year boundary |
| TV-015 | 2024-02-28 | 1 day | 2024-02-29 | Leap year — Feb 29 exists |
| TV-016 | 2025-02-28 | 1 day | 2025-03-01 | Non-leap year — Feb 29 doesn't exist |
| TV-017 | 2024-02-29 | 365 days | 2025-02-28 | Leap year + 365 days → correct |
| TV-018 | 2026-07-15 | 365 days | 2027-07-15 | Full year |

---

## Week Arithmetic

| ID | Reference Date | Duration | Expected | Notes |
|----|---------------|----------|----------|-------|
| TV-019 | 2026-07-15 | 1 week | 2026-07-22 | 1 week = 7 calendar days |
| TV-020 | 2026-07-15 | 2 weeks | 2026-07-29 | 2 weeks = 14 calendar days |
| TV-021 | 2026-12-15 | 4 weeks | 2027-01-12 | Year boundary |
| TV-022 | 2024-02-22 | 1 week | 2024-02-29 | Leap year — crosses Feb 29 |

---

## Edge Cases — Duration Validation

| ID | Reference Date | Duration | Expected |
|----|---------------|----------|----------|
| TV-023 | 2026-07-15 | 0 days | INVALID_DURATION_AMOUNT error |
| TV-024 | 2026-07-15 | -5 days | INVALID_DURATION_AMOUNT error |
| TV-025 | 2026-07-15 | 36501 days | DURATION_LIMIT_EXCEEDED error |
| TV-026 | 2026-07-15 | 36500 days | Valid — 2026-07-15 + 36500 ≈ 2126 |

---

## Unsupported Duration Units

| ID | Duration Unit | Expected |
|----|--------------|----------|
| TV-027 | MONTH, amount=1 | UNSUPPORTED_DURATION_UNIT error |
| TV-028 | YEAR, amount=1 | UNSUPPORTED_DURATION_UNIT error |
| TV-029 | BUSINESS_DAY, amount=5 | UNSUPPORTED_DURATION_UNIT error |
| TV-030 | WORKING_DAY, amount=10 | UNSUPPORTED_DURATION_UNIT error |
| TV-031 | HOUR, amount=48 | UNSUPPORTED_DURATION_UNIT error |

---

## M5 Candidate Integration

| ID | Scenario | Expected |
|----|----------|----------|
| TV-032 | M5 candidate kind=QUALITATIVE_REFERENCE, "unverzüglich" | CALCULATION_NOT_PERFORMED — no duration available |
| TV-033 | M5 candidate kind=EXPLICIT_DATE, "bis zum 31.07.2026" | No reference event needed (explicit date), calculation should use explicit date directly |
| TV-034 | M5 candidate kind=RELATIVE_PERIOD, unit=WEEK, amount=2 | Duration correctly extracted: {amount: 2, unit: "week", calendar_days: 14} |
| TV-035 | M5 candidate kind=RELATIVE_PERIOD, unit=Tag, amount=14 | Duration correctly extracted: {amount: 14, unit: "day", calendar_days: 14} |

---

## Safety and Compliance Gates

| ID | Check | Expected Result |
|----|-------|----------------|
| TV-036 | Any successful calculation response | `human_review_required` === true |
| TV-037 | Any successful calculation response | `legal_validity_assessed` === false |
| TV-038 | Any successful calculation response | `adjustments.weekend_adjustment_applied` === false |
| TV-039 | Any successful calculation response | `adjustments.holiday_adjustment_applied` === false |
| TV-040 | Any successful calculation response | `adjustments.legal_rule_applied` === false |
| TV-041 | Any successful calculation response | `adjustments.delivery_fiction_applied` === false |
| TV-042 | Any successful calculation response | `adjustments.announcement_fiction_applied` === false |
| TV-043 | Any error response | `human_review_required` === true |
| TV-044 | All responses | No instance of word "Frist" in non-warning content |
| TV-045 | All responses | No instance of word "deadline" (except in warning codes) |
| TV-046 | All responses | `calculation_steps` array is present and non-empty |
| TV-047 | All responses | `calculated_date` is valid ISO 8601 date (YYYY-MM-DD) |
| TV-048 | Deterministic output | Same inputs → same outputs on repeated calls |
| TV-049 | No external requests | No HTTP/network calls during calculation |
| TV-050 | No log leakage | Reference dates not present in application log output |

---

## Manual Confirmation Paths

| ID | Scenario | Expected |
|----|----------|----------|
| TV-051 | User manually enters date 2026-07-15 | confirmation_method=MANUALLY_ENTERED, source_type="user_manual" |
| TV-052 | User corrects suggested date from 2026-07-15 to 2026-07-20 | confirmation_method=CORRECTED, source_type="user_manual" |
| TV-053 | User enters invalid date "2026-02-30" | INVALID_DATE error |
| TV-054 | User enters date outside range (1899-01-01) | INVALID_DATE error (before 1900-01-01) |

---

## Audit Trail

| ID | Scenario | Expected |
|----|----------|----------|
| TV-055 | Get confirmation history for candidate with 2 confirmations | Returns 2 entries, sorted by confirmed_at desc |
| TV-056 | Get confirmation history for candidate with revoked confirmation | Most recent entry has status REVOKED, entry[0].supersedes_confirmation_id references prior |
| TV-057 | Confirm then change → get history | Old entry SUPERSEDED, new entry CONFIRMED with supersedes_confirmation_id set |

---

## API Integration

| ID | Scenario | Expected |
|----|----------|----------|
| TV-058 | GET reference-events for RELATIVE_PERIOD candidate with 2 detected events | Returns 200, 2 events with all fields populated: candidate_id (UUID), event_type, suggested_date, source_type, evidence_text, start_offset, end_offset, confirmation_status=UNCONFIRMED |
| TV-059 | Any 4xx error response | Response body uses error envelope: {"detail": {"code": "ERROR_CODE", "message": "Human-readable message"}}. Detail.code and detail.message are present and non-empty. |
| TV-060 | Confirm with explicit candidate_id for existing ReferenceEventCandidate | ConfirmedReferenceEvent.candidate_id matches the requested UUID |
| TV-061 | Confirm without candidate_id (manual entry) | ConfirmedReferenceEvent.candidate_id is null, confirmation_method=MANUALLY_ENTERED |
| TV-062 | Confirm with source_type=auto_detected → confirmation_method mapping | Response shows confirmation_method=auto_suggested |
| TV-063 | Confirm with source_type=user_manual → confirmation_method mapping | Response shows confirmation_method=manually_entered |
| TV-064 | Confirm with source_type=user_corrected → confirmation_method mapping | Response shows confirmation_method=corrected |

---

## Total: 64 Test Vectors

All vectors are specification-only. Implementation in the future build run. Each vector maps to at least one functional requirement or invariant.

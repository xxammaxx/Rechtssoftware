# Contract — Calculation Trace

Every future result returns ordered steps and top-level warnings. Steps distinguish `MATHEMATICAL`, `CALENDAR_CONTEXT`, `HOLIDAY_LOOKUP`, `LEGAL_PROFILE`, and `NOT_APPLIED`; only the latter three may reference dataset/profile provenance. The trace always includes `human_review_required=true` and `legal_validity_assessed=false` in the first M6-B build.

# Product Tests

This directory is reserved for product and Local-only guardrail tests.

Required first tests:

1. outbound network denied
2. Golden Path works offline
3. remote model and cloud OCR dependencies rejected
4. synthetic sensitive markers absent from logs
5. source evidence required for deadline and action candidates
6. human-review gate cannot be bypassed
7. export requires explicit user action

No product test is implemented by the initial scaffold. Website claim tests live in the repository-level `tests/` directory.

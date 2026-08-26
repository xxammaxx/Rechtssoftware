# Local Core

This directory is reserved for BescheidPilot's deterministic local core.

No product implementation exists yet. Any future code must:

- operate without network access
- accept only local inputs
- produce source-linked structured output
- avoid sensitive logging
- expose uncertainty
- require human review before export
- contain no remote LLM, cloud OCR, telemetry, sync, or upload fallback

The binding contract is in `local_only_contract.md`.

# Local Execution Evidence

This document defines the smallest reusable evidence contract harvested from
the KlauselFix integration-test review. It applies to local tests and future
integration harnesses in Rechtssoftware. It is documentation only: it does
not add a second application runtime, a device runner, an inference provider,
or a new dependency.

## Required record

Each reported run should identify:

```text
run_id=<stable local identifier>
captured_at=<local timestamp>
execution_scope=<unit|integration|device|benchmark>
execution_mode=LOCAL_ONLY
command=<exact command or test selector>
result=<PASS|FAIL|NOT_EXECUTED|PARTIAL>
device_test=<NOT_APPLICABLE|NOT_EXECUTED_NO_DEVICE|EXECUTED>
evidence_refs=<paths to readable local evidence>
limitations=<known limits or skipped gates>
```

`PASS` requires an executed command and readable evidence. A skipped device,
model, or hardware step must never be represented as a passing result. When a
physical device is unavailable, use `device_test=NOT_EXECUTED_NO_DEVICE` and
`result=NOT_EXECUTED` or `PARTIAL` as appropriate.

## Target boundaries

- All execution is local. Do not send case data, prompts, outputs, or logs to
  a remote inference, telemetry, OCR, or test service.
- Use only synthetic fixtures for tests; follow the repository's
  `SYNTHETISCH –` fixture convention.
- Do not record secrets, credentials, private case data, or unrestricted
  stack traces. Evidence references must be readable without exposing them.
- Claim memory, thermal, battery, storage, latency, or model quality only
  when the corresponding measurement was actually executed and its method is
  recorded.
- Preserve the existing human-review and evidence-completeness gates. A test
  result is not a legal conclusion and does not establish legal validity.

## Mapping of harvested concepts

| KlauselFix concept | Rechtssoftware handling |
| --- | --- |
| Repeatable local command/result capture | This contract plus existing test commands |
| Lifecycle, interruption, abort, and restart semantics | Existing integration tests, especially exception-boundary and sync-abort/restart coverage |
| Deterministic test data | Existing synthetic fixtures; no KlauselFix fixture copy |
| Device/ADB/Flutter execution | Not applicable to the current target architecture |
| Local model inference and model-specific benchmarks | Not applicable until a separately specified target capability exists |
| Thermal, battery, and resource measurements | Not claimed without an implemented target measurement boundary |

## Review rule

This contract documents evidence semantics only. It must not be used to imply
that a physical device test, local model inference, or hardware benchmark was
executed when it was not. Any future implementation that changes runtime,
trust boundary, persistence, or execution ownership requires its own
architecture decision and acceptance tests.

SOURCE_PROVENANCE=xxammaxx/KlauselFix@4d7ee12b1f1c67bd67488ed7c6333af76ad0475c
HARVEST_DECISION=ADAPT_AND_MIGRATE
ARCHITECTURE_DRIFT=NO

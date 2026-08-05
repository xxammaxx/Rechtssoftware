# Plan — M6-B Calendar Context and Versioned Legal Rule Profiles

**Status:** architecture and work plan only. Implementation is prohibited pending owner approval.

## Selected implementation order

| Order | Slice | Reason |
|---|---|---|
| 1 | M6-B.2 Holiday Data Foundation | Rule profiles require dated, jurisdiction-bound source provenance. |
| 2 | M6-B.1 Calendar Context | Can safely expose weekday/weekend and verified source context without a legal adjustment. |
| 3 | M6-B.3 Versioned Rule Profiles | Requires the source and trace foundations above. |
| Deferred | M6-B.4 Delivery/Announcement Fictions | High factual/legal sensitivity; separate source and owner gate. |

## Future architecture (no files are created now)

| Layer | Future responsibility | Must not do |
|---|---|---|
| Domain | Immutable value objects for dataset version, holiday context, rule profile selection and trace step | infer legal applicability |
| Application | Validate explicit inputs and orchestrate trace construction | choose profile/jurisdiction |
| Infrastructure | Read local signed/hashed data package and SQLite persistence if approved | fetch external data |
| API/UI | Show inputs, warnings, source/version and explicit confirmation controls | label a result legally binding |

## Future dependency graph

```text
confirmed M6-A reference event + duration
                |
                v
calendar date / weekend context ------> calculation trace
                |                              ^
                v                              |
local verified holiday dataset --- explicit jurisdiction
                |                              |
                +--> explicit selected rule profile (later only)
```

## First build contract

The first build begins only after owner approval and is restricted to M6-B.2. It may introduce a **schema and validator**, but it may not ship a production holiday JSON file, migrate production data, expose a UI calculation, or apply a legal rule. An implementation proposal must define a reversible migration/rollback plan before any persistence change.

## Verification contract

- Unit tests for date, validity intervals, manifest hashes and profile selection gates.
- Integration tests for local-only loading, invalid/expired package rejection, no external request and rollback.
- UI/browser and keyboard/Axe tests only after a UI exists.
- Security review precedes Compliance review.
- Full local pytest, Ruff 0, mypy, pip check, coverage and changed-lines coverage are required before a future local commit.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| User treats context as legal determination | permanent non-binding label, structured warnings, mandatory human review |
| State/local exception flattened | scope fields; block result for unknown/local scope |
| Stale legal source | validity interval + immutable version + hash + review date |
| Silent profile choice | no default profile; explicit selection/revoke lifecycle |
| Factual delivery data guessed | entire M6-B.4 deferred |
| Data leakage | no runtime requests, no PII in logs, synthetic-only tests |

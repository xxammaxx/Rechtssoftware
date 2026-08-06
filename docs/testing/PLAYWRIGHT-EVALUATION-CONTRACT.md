# RC-026-R2 Playwright Evaluation Contract

**Generated:** 2026-08-05  
**Runcard:** RC-026-R2 Phase E  

---

## QUALITY_DIMENSIONS

| Dimension | Description | Threshold |
|-----------|-------------|-----------|
| functional_correctness | UI workflows produce correct results | 100% mandatory scenarios GREEN |
| browser_observability | No console errors, no page errors, no external requests | 0 unexpected errors |
| data_integrity | Data survives restart, no duplicate records | 0 data loss, 0 duplicate mutations |
| security | CSP, CSRF, host validation, no secrets in DOM | 0 security violations |
| privacy | No case data in logs, no external assets, no telemetry | 0 privacy violations |
| accessibility | axe-core: no critical or serious violations | 0 critical, 0 serious |
| responsive_layout | No horizontal overflow at mandatory viewports | 0 overflow at 1920/1280/1024/390 |
| restart_persistence | Data survives server restart | 0 data loss after restart |
| idempotency | Double submits produce no duplicate records | 0 duplicate mutations |
| current_historical_search_separation | Standard search shows only CURRENT | Must match ADR-010 behavior |
| release_installation_fidelity | Tests run against installed wheel, not source checkout | Import from site-packages only |

## EVALUATION_DATASET

All data exclusively synthetic:
- Synthetic case: "SYNTHETISCH – Playwright E2E Testfall"
- Synthetic PDF: Generated via pymupdf with test text
- Synthetic deadline: "Bescheid vom 15.06.2026"
- No real names, no real case numbers, no production GII mutations

## DETERMINISTIC_ASSERTIONS

- No `or True`, no tautologies
- No `catch-and-ignore` around assertion errors
- No assertions based solely on text length
- No critical actions bypassed via direct DB manipulation

## PASS_THRESHOLDS

```
100% mandatory scenarios GREEN
0 unexpected console errors
0 page errors
0 external requests (except gesetze-im-internet.de for GII)
0 axe critical
0 axe serious
0 horizontal overflow at mandatory viewports
0 duplicate mutations
0 data loss after restart
0 source-checkout imports
```

## KNOWN_FAILURE_CLASSES

| Class | Treatment |
|-------|-----------|
| Test data not seeded | Skip with note, not fail |
| GII live sync (no approval) | Skip, not execute |
| Firefox/WebKit unsupported | Skip with note (Chromium is mandatory) |
| axe moderate/minor violations | Log, not block |

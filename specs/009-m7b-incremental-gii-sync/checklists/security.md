# Security Threat Model — M7-B Incremental GII Sync

## Threat Model Overview

**Asset:** Legal corpus integrity and availability.
**Attacker model:** Network attacker (MitM), malicious source server, local user error.
**Trust boundary:** Local machine ↔ GII server (HTTPS).

---

## Threat Matrix

| ID | Threat | Vector | Impact | Likelihood | Mitigation |
|----|--------|--------|--------|------------|------------|
| T01 | Catalog manipulation | MitM modifies gii-toc.xml during download | Wrong items downloaded; items classified incorrectly | LOW (HTTPS + TLS) | HTTPS enforced; SHA-256 of catalog stored; compare against last known hash |
| T02 | Replay of stale catalog | Attacker serves old gii-toc.xml | Missing new instruments; unable to detect changes | LOW | catalog_stand_date comparison; --force flag requires explicit user intent |
| T03 | DoS via oversized catalog | Server returns 100 MB catalog XML | Resource exhaustion; OOM | LOW | SourceClient has 200 MB limit; catalog typically 300-500 KB |
| T04 | Path traversal via instrument key | `--instrument "../../etc/passwd"` | Unauthorized file read | LOW | Key validation: `^[a-zA-Z0-9_ -]+$` |
| T05 | Corrupted snapshot on disk | Disk error or tampering | False sense of corpus integrity | LOW | SHA-256 verify command; integrity check at read time |
| T06 | Snapshot dedup collision | SHA-256 collision (theoretical) | Wrong content mapped to wrong instrument | NEGLIGIBLE | SHA-256 is cryptographically collision-resistant |
| T07 | Sync log injection | Error message contains malicious content | Log injection attack | LOW | error_summary truncated to 500 chars; no newlines allowed |
| T08 | Concurrent sync runs | User starts two syncs simultaneously | Double-writes; race condition | LOW | Lock file or database flag prevents concurrent runs |
| T09 | Sensitive data in sync URLs | Instrument name in URL logged | Information disclosure (no PII in law names, but metadata leak) | LOW | URLs are public law names; no case data in sync |
| T10 | Catalog parse XXE | Malicious gii-toc.xml with XXE payload | SSRF; file read | LOW | Inherited from M7-A: resolve_entities=False in lxml parser |
| T11 | HTTP redirect to malicious host | GII server compromised, redirects to attacker host | Malicious content downloaded as law XML | LOW | SourceClient validates redirect targets; host allowlist enforced |
| T12 | Force mode bypasses safety | User runs `--force` without understanding | Inadvertent full re-download | MEDIUM | Force mode only skips stand-date gate; SHA-256 dedup still active; explicit flag required |

---

## Security Requirements

| ID | Requirement | Related Threat |
|----|-------------|---------------|
| SEC-M7B-01 | All HTTP downloads MUST use HTTPS. HTTP for external hosts is BLOCKED. | T01 |
| SEC-M7B-02 | The catalog XML MUST be validated against size limits before parsing. | T03 |
| SEC-M7B-03 | Instrument keys MUST be validated against `/^[a-zA-Z0-9_ -]+$/`. | T04 |
| SEC-M7B-04 | Snapshot integrity MUST be verifiable via SHA-256 recomputation. | T05 |
| SEC-M7B-05 | Error summaries MUST be truncated to 500 characters. | T07 |
| SEC-M7B-06 | Concurrent sync runs MUST be prevented. | T08 |
| SEC-M7B-07 | Sync logs MUST NOT contain personal data or case data. | T09 |
| SEC-M7B-08 | XML parsing MUST use the existing secure lxml configuration. | T10 |
| SEC-M7B-09 | Redirect targets MUST be validated against the host allowlist. | T11 |
| SEC-M7B-10 | The `--force` flag MUST require explicit user action (not default). | T12 |

---

## Security Test Cases

| ID | Test | Expected |
|----|------|----------|
| ST-01 | Invalid instrument key: `../../etc/passwd` | CLI error: "Invalid instrument key" |
| ST-02 | GII URL with HTTP (not HTTPS) | Blocked by SourceClient policy |
| ST-03 | Concurrent sync start | Second run blocked: "Sync already in progress" |
| ST-04 | Very large catalog simulation | Limited by SourceClient max_response_bytes |
| ST-05 | Catalog with XXE payload | lxml raises XMLSyntaxError; snapshot marked FAILED |
| ST-06 | Redirect to non-allowlisted host | Blocked by SourceClient redirect validation |
| ST-07 | Error summary with newlines | Truncated; safe_log_event strips/escapes |
| ST-08 | Dry-run with --force flag | Plan created; warning "Force mode active" displayed |

---

## Audit Trail

Every sync operation produces audit-relevant data:

| What | Where | Retention |
|------|-------|-----------|
| SyncRun metadata | sync_runs table | 90+ days (configurable) |
| Per-item status | sync_items table | Linked to sync_run (CASCADE DELETE) |
| HTTP response headers | sync_items (etag, last_modified, status) | Same as sync_items |
| Import snapshots | legal_source_snapshots | Immutable; never deleted |
| Integrity failures | sync_items.error_summary | Same as sync_items |

**Recovery:** In case of compromise, `pln sync verify` detects snapshot corruption. `pln sync gii --apply --force` re-downloads all instruments to restore integrity.

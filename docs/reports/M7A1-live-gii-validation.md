# M7-A.1 — Live GII Validation Report

**Generated:** 2026-07-23T10:54:00Z
**Agent:** issue-orchestrator
**Source:** https://www.gesetze-im-internet.de/

---

## 1. Test Object

- **Law:** Zehntes Buch Sozialgesetzbuch (SGB X)
- **Official Title:** Zehntes Buch Sozialgesetzbuch - Sozialverwaltungsverfahren und Sozialdatenschutz -
- **Abbreviation:** SGB X
- **Authority Tier:** CONSOLIDATED_NON_OFFICIAL
- **Instrument Type:** STATUTE

---

## 2. Live Sync Evidence

| Property | Value |
|----------|-------|
| Timestamp (UTC) | 2026-07-23T10:38:51.125427 |
| Final URL | https://www.gesetze-im-internet.de/sgb_10/xml.zip |
| HTTP Status | 200 |
| Content-Type | application/zip |
| Byte Size | 130,034 (downloaded, compressed) |
| Provisions Imported | 137 |
| Snapshot SHA-256 | 92cf720d98796f9781d4605eb6a6bcd739f71d9a642e15a8e538e8b7c79e16bc |
| Storage Path | snapshots/92/92cf720d98796f9781d4605eb6a6bcd739f71d9a642e15a8e538e8b7c79e16bc.xml |
| Snapshot ID | 515ee063-7145-4b0d-9b5e-0833561597f7 |
| Source Key | gesetze-im-internet |

---

## 3. Content-Addressed Storage & Deduplication

| Metric | Before 1st Sync | After 1st Sync | After 2nd Sync | After 3rd Sync (Post-Restart) |
|--------|-----------------|----------------|----------------|------------------------------|
| Content files | 0 | 1 | 1 | 1 |
| DB snapshots | 0 | 1 | 1 | 1 |
| DB provisions | 0 | 137 | 137 | 137 |
| DB instruments | 0 | 1 | 1 | 1 |

**Dedup confirmed:** No duplicate content files or database rows created across 3 syncs.

---

## 4. CLI Integrity Verification

| Check | Result |
|-------|--------|
| Hash matches | ✅ `92cf720d...` |
| File exists | ✅ |
| Size matches | ✅ |
| Status | VERIFIED |

---

## 5. Citation Resolution

**Query:** `§ 48 SGB X`
**Result:** ✓ Found — § 48 Aufhebung eines Verwaltungsaktes mit Dauerwirkung bei Änderung der Verhältnisse

---

## 6. FTS Search

**Query:** `Verwaltungsverfahren`
**Results:** 10 matching provisions in SGB X (including § 8, § 9, § 16, § 17, § 18, etc.)

---

## 7. Negative Tests

| Test | Expected | Actual | Pass |
|------|----------|--------|------|
| Non-existent instrument | Error: not found | Error: not found in GII catalog | ✅ |
| Corrupted snapshot file | HASH_MISMATCH, FAILED | FAILED, HASH_MISMATCH | ✅ |
| Missing snapshot file | FILE_NOT_FOUND, MISSING | MISSING, FILE_NOT_FOUND | ✅ |
| Re-sync after corruption | File overwritten, VERIFIED | VERIFIED | ✅ |

---

## 8. Network

- **DNS:** www.gesetze-im-internet.de → 195.74.94.216
- **TLS:** HTTPS-only enforced (TransportPolicy.PRODUCTION)
- **Redirect validation:** Active
- **Host allowlist:** gesetze-im-internet.de
- **No proxy:** Direct connection

---

## 9. Known Issues

- **Cosmetic:** Citation resolution output uses Unicode checkmark (✓) which fails on Windows cp1252 console. Workaround: `PYTHONIOENCODING=utf-8`.

---

## 10. Verdict

✅ **GII Live Sync: PASSED** — Real download, SHA-256 content addressing, deduplication, integrity verification, citation resolution, and FTS search all confirmed with live data from gesetze-im-internet.de.

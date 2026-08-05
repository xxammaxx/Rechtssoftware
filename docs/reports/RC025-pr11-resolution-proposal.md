# RC-025 PR #11 Resolution Proposal

**PR:** #11 — "release: make PrivateLegalNavigator v1.0.0-rc.1 installable and releasable"
**Commit:** `35742bbfd1732a86dd4360500b268f6ef8089d68`
**Branch:** `safety/pr11-35742bb` (local safety copy)

## Verdict: `SUPERSEDED`

PR #11 is almost entirely superseded by the release candidate branch (`release/v1.0.0-rc.2-reconciled` → `feat/product-ux-design-evolution-v1`).

## Content Comparison

### Already Present in HEAD (Superseded)

| PR #11 Content | Status | Notes |
|----------------|--------|-------|
| Version bump to 1.0.0rc1 | Superseded | HEAD is at 1.0.0rc2 |
| CLI entry point (`private-legal-navigator`) | Present | Already in pyproject.toml |
| Windows scripts (7 files) | Present | All 7 in `release/windows/` + extra `test-cold-install.ps1` |
| User docs (7 files) | Present | All in `docs/user/` |
| Release docs (V1-DEFINITION-OF-DONE, V1-RELEASE-CHECKLIST, V1-VALIDATION-REPORT) | Present | All in `docs/release/` |
| CHANGELOG.md | Present | More detailed version in HEAD |
| README.md updates | Present | Further updated in HEAD |
| Release artifacts (wheel, sdist, ZIP) | Regenerated | HEAD has rc2 versions; RC-025 requires these be generated, not versioned |
| MyPy fix (lxml override) | Different approach | HEAD pyproject.toml handles differently; no action needed |
| Package data (static/**/*.js removal) | Different | HEAD includes `static/**/*.js` (needed for JS assets) |

### Not in HEAD / Potentially Relevant

| PR #11 Change | Assessment | Recommendation |
|---------------|------------|----------------|
| Cross-case check removal in `reference_event_routes.py` | Security regression | Do NOT port — cross-case enforcement is a security feature |
| `sync_run_id` removal from CLI status output | Minor UI change | Low priority; can be evaluated separately |
| `specs/009-m7b-incremental-gii-sync/tasks.md` checkbox updates | Already diverged | HEAD has independent task tracking |

### Generated Artifacts (Should Be Removed from Version Control)

Per RC-025 Section 11 (Phase G3), the following artifacts in PR #11 should be generated, not versioned:
- `dist/*.whl`, `dist/*.tar.gz`
- `release/output/*.whl`, `release/output/*.tar.gz`, `release/output/*.zip`

HEAD currently also has `dist/` versioned — this will be addressed in Phase G.

## Recommendation

1. **PR #11 Status:** `SUPERSEDED` — Do not merge. Most content is already in HEAD or superseded by newer work.
2. **No porting needed:** The selective port (`d2ed916`) already ensured relevant PR #11 content made it into the RC branch.
3. **Future action:** After RC-025 completion and independent verification, PR #11 can be closed with a comment referencing the superseding commits.
4. **Windows scripts:** Already present and enhanced in HEAD (`test-cold-install.ps1` added).
5. **Security note:** PR #11's cross-case enforcement removal must NOT be merged — it weakens security (Constitution §8, §10). HEAD preserves the correct enforcement.

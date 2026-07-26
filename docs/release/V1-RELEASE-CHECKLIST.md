# V1.0 Release Checklist — PrivateLegalNavigator

**Version:** v1.0.0-rc.1
**Date:** 2026-07-26
**Branch:** `release/v1-installable-closure`

## Pre-Release Gates

| # | Gate | Status | Evidence |
|---|------|--------|----------|
| 1 | All tests pass | ✅ PASS | 906/906 (Python 3.11 + 3.14) |
| 2 | Coverage ≥ 71% | ✅ PASS | 78% |
| 3 | Ruff clean | ✅ PASS | 0 errors |
| 4 | Mypy strict clean | ✅ PASS | 0 errors |
| 5 | pip check | ✅ PASS | No broken requirements |
| 6 | Wheel build | ✅ PASS | `private_legal_navigator-1.0.0rc1-py3-none-any.whl` |
| 7 | sdist build | ✅ PASS | `private_legal_navigator-1.0.0rc1.tar.gz` |
| 8 | twine check | ✅ PASS | Both pass |
| 9 | Install from wheel | ✅ PASS | Fresh Python 3.11 venv |
| 10 | CLI entry point | ✅ PASS | `private-legal-navigator --version` → `1.0.0rc1` |
| 11 | Templates in wheel | ✅ PASS | 14 HTML templates + CSS |
| 12 | Cross-case isolation | ✅ PASS | Fixed per security review |
| 13 | Security review | ✅ PASS | 14 checks (13 PASS, 1 fixed) |
| 14 | Version consistency | ✅ PASS | pyproject.toml = README = CHANGELOG = `__version__` |

## Release Artifact Gates

| # | Gate | Status | Evidence |
|---|------|--------|----------|
| 15 | Windows ZIP built | ✅ PASS | `PrivateLegalNavigator-v1.0.0-rc.1-windows.zip` |
| 16 | SHA256SUMS.txt | ✅ PASS | 3 entries |
| 17 | RELEASE-NOTES.md | ✅ PASS | Complete |
| 18 | INSTALLATION-KURZANLEITUNG.txt | ✅ PASS | German quickstart |

## Documentation Gates

| # | Gate | Status | Evidence |
|---|------|--------|----------|
| 19 | V1-DEFINITION-OF-DONE.md | ✅ PASS | `docs/release/` |
| 20 | INSTALL-WINDOWS.md | ✅ PASS | `docs/user/` |
| 21 | USER-GUIDE.md | ✅ PASS | `docs/user/` |
| 22 | FIRST-START.md | ✅ PASS | `docs/user/` |
| 23 | BACKUP-RESTORE.md | ✅ PASS | `docs/user/` |
| 24 | UPGRADE.md | ✅ PASS | `docs/user/` |
| 25 | UNINSTALL.md | ✅ PASS | `docs/user/` |
| 26 | TROUBLESHOOTING.md | ✅ PASS | `docs/user/` |
| 27 | KNOWN-LIMITATIONS.md | ✅ PASS | `docs/user/` |
| 28 | README truth mirror | ✅ PASS | Updated with real numbers |
| 29 | CHANGELOG updated | ✅ PASS | v1.0.0-rc.1 entry |

## Windows Script Gates

| # | Gate | Status | Evidence |
|---|------|--------|----------|
| 30 | install.ps1 | ✅ PASS | Idempotent, no admin |
| 31 | start.ps1 | ✅ PASS | Healthcheck, browser |
| 32 | stop.ps1 | ✅ PASS | Own process only |
| 33 | backup.ps1 | ✅ PASS | SHA-256 manifest |
| 34 | restore.ps1 | ✅ PASS | Integrity validation |
| 35 | uninstall.ps1 | ✅ PASS | Keep data / Purge |

## GitHub Completion Gates

| # | Gate | Status | Evidence |
|---|------|--------|----------|
| 36 | Branch pushed | ⬜ TODO | Push `release/v1-installable-closure` |
| 37 | PR created | ⬜ TODO | Draft PR |
| 38 | Git tag | ⬜ TODO | `v1.0.0-rc.1` |
| 39 | Issues updated | ⬜ TODO | #6, #9 |
| 40 | Release created | ⬜ OWNER | Requires owner approval |

## Final Classification

**GREEN_V1_RC_INSTALLABLE** — All implementable gates pass. Awaiting owner push/PR/release approval.

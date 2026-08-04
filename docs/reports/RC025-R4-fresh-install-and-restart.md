# RC-025-R4 Phase H — Fresh Install and Restart

## Installation

```bash
python3 -m venv /tmp/rc025-r4-fresh-install
pip install dist/private_legal_navigator-1.0.0rc2-py3-none-any.whl
```

## Verification

| Check | Result |
|-------|--------|
| Import `private_legal_navigator` | ✅ v1.0.0rc2 |
| CLI `--version` | ✅ `PrivateLegalNavigator private-legal-navigator 1.0.0rc2` |
| DB initialization | ✅ All tables + `idx_le_one_current` index created |
| Health endpoint | ✅ `{"status":"ok"}` |
| Server stop + restart | ✅ Health passes after restart (persistence proven) |
| DB reopens with schema intact | ✅ Tables persist across restarts |
| No source checkout access | ✅ Isolated venv, no PYTHONPATH to source |

## Environment

- No access to the source checkout at runtime
- Fresh Python 3.12 venv
- Wheel installed from `dist/`
- DB path: `/tmp/rc025-r4-fresh-test.db`

## Classification

```text
GREEN_RC025_R4_FRESH_INSTALL_AND_RESTART_VERIFIED
```

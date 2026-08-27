# Agent Instructions

This repo is a HACS custom component. Keep these in sync on every functional change:

- `custom_components/aircon_ir/manifest.json` — **always bump `version`** (e.g. `0.3.0` → `0.3.1` patch, `0.4.0` minor). `domain` must stay `aircon_ir`, `integration_type` `device`, `dependencies` includes `infrared`.
- `custom_components/aircon_ir/const.py` — `DOMAIN` must match manifest.
- `custom_components/aircon_ir/strings.json` + `translations/en.json` — any new `config_flow` fields or `climate` attributes need translations.
- `hacs.json` — `name`/`homeassistant` constraints if changed (no version field; version comes from manifest).
- `README.md` — copy-paste install path is `/config/custom_components/aircon_ir`, update if domain/features change.

Checks before push:

```bash
python3 -m py_compile custom_components/aircon_ir/*.py && cat custom_components/aircon_ir/manifest.json
```

Version tags: `git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z` after pushing `main`.

Symlink: `CLAUDE.md -> AGENTS.md` — keep in sync (`ln -s AGENTS.md CLAUDE.md`).

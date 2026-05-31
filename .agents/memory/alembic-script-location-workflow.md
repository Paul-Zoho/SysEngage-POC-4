---
name: Alembic script_location — absolute path required when run from workspace root
description: When alembic is invoked from the workspace root (not from sysengage/), the relative script_location = "alembic" in the ini resolves against CWD and fails with "Path doesn't exist: alembic".
---

## Rule
After loading `AlembicConfig`, always override `script_location` with the absolute path:

```python
_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
```

**Why:** `alembic.ini` has `script_location = alembic` (relative path). When invoked via a Replit workflow (`python -u sysengage/run_*.py`), CWD is `/home/runner/workspace` not `sysengage/`. Alembic resolves the relative path against CWD, finds no `alembic/` directory there, and raises `CommandError: Path doesn't exist: alembic`. Setting the absolute path bypasses this CWD sensitivity.

**How to apply:** Every orchestrator script that calls `alembic_command.upgrade` must include the `set_main_option` line. This is idempotent and safe when CWD is already `sysengage/`.

The Replit workflow command is always `python -u sysengage/<runner>.py` from workspace root, so this fix is always required for workflow-invoked runners.

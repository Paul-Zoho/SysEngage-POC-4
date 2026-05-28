---
name: Alembic JSONB server_default syntax
description: How to correctly specify server defaults for JSONB columns in Alembic migrations
---

## Rule
Use a bare Python string `"[]"` or `"{}"` for JSONB `server_default` in Alembic column definitions. Do NOT use `"'[]'::jsonb"` or `sa.text("'[]'::jsonb")`.

**Why:** Alembic wraps plain Python strings in single quotes when emitting DDL. Passing `"'[]'::jsonb"` results in `DEFAULT '''[]''::jsonb'` in the generated SQL — which is invalid JSON/JSONB syntax and raises `InvalidTextRepresentation`.

**How to apply:** Any time you add a JSONB column with a server default in an Alembic migration, write:
```python
sa.Column("my_col", postgresql.JSONB(), server_default="[]", nullable=False)
# or for objects:
sa.Column("my_col", postgresql.JSONB(), server_default="{}", nullable=False)
```
For timestamp defaults, use `sa.text("NOW()")` — timestamps require the explicit cast.

## Reference migration
`sysengage/alembic/versions/012_add_domain_tables.py` — the `register.member_ids` column uses `server_default="[]"` correctly.

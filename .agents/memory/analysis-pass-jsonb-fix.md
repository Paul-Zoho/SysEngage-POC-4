---
name: analysis_pass json→jsonb migration
description: The outputs and declared_transformation_modes columns on analysis_pass were json not jsonb; fixed in migration 014.
---

## Rule
SQLAlchemy JSONB subscript notation (`AnalysisPassModel.outputs["key"]`) generates `outputs['key']` SQL which only works on PostgreSQL `jsonb` type, not `json` type. The `analysis_pass` table initially had both `outputs` and `declared_transformation_modes` as plain `json` despite the model declaring `JSONB`.

**Why:** The initial schema migration used `postgresql.JSONB(astext_type=sa.Text())` in Python, but the column ended up as `json` in the DB (possibly a schema timing or ORM issue). Any query using `column["key"]` subscript or `.as_integer()` will raise `psycopg2.errors.DatatypeMismatch: cannot subscript type json`.

**Fix applied:** Migration 014 (`sysengage/alembic/versions/014_cast_json_cols_to_jsonb.py`) does:
```sql
ALTER TABLE analysis_pass ALTER COLUMN outputs TYPE jsonb USING outputs::jsonb;
ALTER TABLE analysis_pass ALTER COLUMN declared_transformation_modes TYPE jsonb USING declared_transformation_modes::jsonb;
```

**How to apply:** If you add another `JSONB` column to any table, verify the actual DB type after migration with:
```python
s.execute(text("SELECT udt_name FROM information_schema.columns WHERE table_name='...' AND column_name='...'"))
```
If the result is `('json',)` instead of `('jsonb',)`, write a migration to cast it.

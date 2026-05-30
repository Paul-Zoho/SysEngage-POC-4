---
name: Neon branch merge — JSONB and sequence gotchas
description: Two psycopg2 pitfalls when copying rows that contain JSONB columns across Neon branches using SQLAlchemy text() queries.
---

## Gotcha 1 — JSONB columns need explicit serialisation

When reading a row via SQLAlchemy `text()` from a source branch, JSONB columns (`outputs`, `declared_transformation_modes`, `signal_refs`) are returned as Python `dict` / `list` objects. psycopg2 cannot bind these directly and raises `can't adapt type 'dict'`.

**Fix:** Serialise to a JSON string with `json.dumps(val)` and use `CAST(:col AS JSONB)` in the INSERT statement:

```python
def _jsonb(val):
    if val is None: return None
    return json.dumps(val) if not isinstance(val, str) else val

# In INSERT:
"CAST(:outputs AS JSONB), CAST(:declared_transformation_modes AS JSONB)"
```

## Gotcha 2 — Sequence position may equal explicitly-inserted IDs

When you INSERT rows with **explicit** primary key values (bypassing the sequence), the sequence counter does not advance. If the combined branch's sequence was inherited at position N and you then INSERT rows with explicit IDs N, N+1, … calling `nextval('p_id_seq')` still returns N — causing a duplicate-key violation.

**Fix:** After any block of explicit-ID inserts, advance the sequence to the current max before asking for new IDs:

```sql
SELECT setval('p_id_seq',
    (SELECT max(cast(substring(pass_id from 2) as integer)) FROM analysis_pass));
```

Then `nextval` returns max+1, max+2, … safely.

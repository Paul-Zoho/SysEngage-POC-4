---
name: Neon SSL drop across AI call phases
description: RD mechanism holds a DB session open across multi-minute AI call phases; Neon serverless endpoint suspends and tears down all pool SSL connections. Fix pattern documented here.
---

## Rule

Never hold a SQLAlchemy session (and therefore a pooled connection) open across an AI call phase that can run for 3-5+ minutes.  Neon serverless endpoints auto-suspend after ~5 minutes of idle time and send an SSL `close_notify` to all connections in the pool.

## Why it fails in two ways

1. **Crash on `session.close()`** — when the mechanism tries to close the session after AI calls, SQLAlchemy issues a `ROLLBACK` before releasing the connection.  That ROLLBACK hits the dead SSL connection and raises `psycopg2.OperationalError: SSL connection has been closed unexpectedly`.  Using `session.close()` directly on a dead session is not safe.

2. **Crash on first stage4 query** — if `session.close()` somehow succeeds, the new `get_session()` checks out a connection from the pool.  The pool still holds connections from before the AI phase; `pool_pre_ping=True` does not reliably catch SSL-level teardowns (OS may buffer `close_notify`), so the dead connection passes the ping and the first real query fails.

## Fix pattern

### `core/db.py` — add `refresh_engine_pool()`

```python
def refresh_engine_pool() -> None:
    engine.dispose()       # closes ALL pooled connections without network I/O — safe on a dead pool
    _wait_for_db(_database_url)  # blocks until Neon endpoint has fully resumed
```

`engine.dispose()` is safe to call even when all pool connections are dead — it never touches the network.  `_wait_for_db` retries `SELECT 1` with a fresh probe engine until the endpoint responds (up to 60 s).

### `mechanisms/requirement_derivation/__init__.py` — before stage4

```python
session.invalidate()       # marks connection dead, suppresses ROLLBACK-on-close
refresh_engine_pool()      # dispose pool + wait for endpoint
session = get_session()    # genuinely fresh connection
```

`session.invalidate()` is the correct way to abandon a potentially-dead session — it does NOT attempt a ROLLBACK.

### `run_dispatch.py` — before each RD row in the dispatcher loop

```python
refresh_engine_pool()
r = rd.run_requirement_derivation(...)
```

The dispatcher engine is shared across the entire multi-pass, multi-row run.  By the time pass 3d runs, the pool may be holding connections that aged across passes 3a→3b→3c.  Purging before each RD row ensures stage1 reads also start on a fresh connection.

### `run_pmt_rd_r5_rerun.py` (and all targeted rerun scripts)

```python
refresh_engine_pool()
result = rd.run_requirement_derivation(...)
```

Same rationale: alembic migration at step 4 uses the pool; by the time step 5 runs the pool connection may already be stale.

## How to apply

Any script or dispatcher loop that runs RD (or any AI-heavy mechanism) after a gap longer than ~3 minutes of no DB activity should call `refresh_engine_pool()` before the mechanism entry point, AND the mechanism itself should call `session.invalidate(); refresh_engine_pool(); session = get_session()` before its write stage.

## What NOT to use

- `pool_pre_ping=True` alone — does not handle SSL-level teardowns reliably.
- TCP keepalives (`keepalives=1` etc.) — do not prevent Neon endpoint suspension.
- `session.close()` on a potentially-dead session — triggers ROLLBACK, which crashes.
- `engine.dispose()` alone without `_wait_for_db` — endpoint may still be waking up when `get_session()` fires, causing the fresh connection attempt to also fail.

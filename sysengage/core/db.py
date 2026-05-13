"""
Database session management for SysEngage.

Architectural commitment: Neon PostgreSQL via SQLAlchemy 2.x.
Per Row 4 Applied §5 — connection pool, session factory, engine configuration.

Connection priority:
  1. NEON_DATABASE_URL — original Replit-managed Neon instance (canonical data).
  2. DATABASE_URL      — Replit Helium Postgres (fallback only).

DSN sanitisation:
  NEON_DATABASE_URL (set by Replit's Neon→Helium migration) contains
  channel_binding=require.  Neon's PgBouncer pooler supports only
  SCRAM-SHA-256, not SCRAM-SHA-256-PLUS (the channel-binding variant).
  libpq ≥ 14 enforces require strictly, so the auth handshake fails.
  We normalise to channel_binding=prefer, which uses the upgrade when
  the server supports it but does not fail when it does not.

Cold-start handling:
  When Neon's compute is suspended the pooler accepts the TCP connection
  but PostgreSQL takes 15-30 s to wake. We retry actual SELECT 1 calls
  (not raw socket probes) for up to 60 s before giving up.
"""

import os
import sys
import time
import re
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

import psycopg2  # noqa: F401 — imported here for libpq version log below


def _sanitise_dsn(url: str) -> str:
    """
    Rewrite channel_binding=require → channel_binding=prefer in *url*.

    Neon's PgBouncer pooler does not support SCRAM-SHA-256-PLUS (the
    channel-binding variant of SCRAM). libpq ≥ 14 enforces 'require'
    strictly, causing auth to fail against the pooler. 'prefer' retains
    the security upgrade when the server supports it.
    """
    if "channel_binding=require" not in url:
        return url
    return url.replace("channel_binding=require", "channel_binding=prefer")


def _wait_for_db(url: str, timeout_s: int = 60) -> None:
    """
    Retry a real SELECT 1 connection until Neon's compute is ready or
    *timeout_s* expires.  Raw socket probing is not a valid DB-readiness
    check (the pooler accepts TCP while PostgreSQL is still starting),
    so we test an actual authenticated query here.

    Raises nothing — if Neon is still starting when the timeout expires
    we let SQLAlchemy's create_engine do its own connect_timeout handling.
    """
    from sqlalchemy import create_engine as _ce, text as _t

    probe_engine = _ce(url, pool_size=1, max_overflow=0,
                       connect_args={"connect_timeout": 5})
    deadline = time.time() + timeout_s
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            with probe_engine.connect() as conn:
                conn.execute(_t("SELECT 1"))
            probe_engine.dispose()
            if attempt > 1:
                print(f"Neon ready after {attempt} probe(s).", file=sys.stderr)
            return
        except Exception:
            time.sleep(3)
    probe_engine.dispose()
    print("Neon probe timed out — proceeding anyway.", file=sys.stderr)


# ── select database URL ────────────────────────────────────────────────────────

_raw_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "No database URL configured. Set NEON_DATABASE_URL (Neon) or DATABASE_URL."
    )

_database_url = _sanitise_dsn(_raw_url)

# Log libpq version once at startup — helps diagnose future auth issues.
import psycopg2 as _pg2
print(
    f"[db] libpq {_pg2.__libpq_version__} | "
    f"{'Neon (NEON_DATABASE_URL)' if os.environ.get('NEON_DATABASE_URL') and _raw_url == os.environ['NEON_DATABASE_URL'] else 'Helium (DATABASE_URL)'}",
    file=sys.stderr,
)

# Warm Neon before the persistent engine is created so the first CLI
# run after a suspend succeeds without a manual retry.
if (
    os.environ.get("NEON_DATABASE_URL")
    and _raw_url == os.environ["NEON_DATABASE_URL"]
):
    _wait_for_db(_database_url)

# ── persistent engine ─────────────────────────────────────────────────────────

engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 30},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    """Return a new SQLAlchemy session. Caller is responsible for close/commit/rollback."""
    return SessionLocal()


def get_next_sequence_value(session: Session, sequence_name: str) -> int:
    """Fetch the next value from a named Postgres sequence."""
    result = session.execute(text(f"SELECT nextval('{sequence_name}')"))
    return result.scalar_one()


def get_next_n_sequence_values(
    session: Session, sequence_name: str, n: int
) -> list[int]:
    """
    Fetch n consecutive values from a named Postgres sequence in ONE round trip.

    Uses generate_series to call nextval n times server-side, avoiding n
    individual round trips.  Critical for bulk-inserting large atom sets
    (e.g. 1000-atom single-paragraph inputs) within the 10-second latency budget.
    """
    if n <= 0:
        return []
    result = session.execute(
        text(
            f"SELECT nextval('{sequence_name}') "
            f"FROM generate_series(1, :n)"
        ),
        {"n": n},
    )
    return [row[0] for row in result.fetchall()]


def format_identifier(prefix: str, seq_val: int) -> str:
    """
    Format a canonical ledger identifier.

    Per canonical ledger spec v2.9: zero-pad to 3 digits minimum; extends
    automatically for larger numbers (S001..S999, S1000, S10000).
    Finding F18: uses canonical prefixes (S, SEG, SA, P) not replit.md prefixes.
    """
    digits = max(3, len(str(seq_val)))
    return f"{prefix}{seq_val:0{digits}d}"

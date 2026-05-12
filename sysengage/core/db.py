"""
Database session management for SysEngage.

Architectural commitment: Neon PostgreSQL via SQLAlchemy 2.x.
Per Row 4 Applied §5 — connection pool, session factory, engine configuration.

Connection priority:
  1. NEON_DATABASE_URL — external Neon project (canonical target).
  2. DATABASE_URL      — Replit-managed Helium Postgres (test/CI fallback only).

Cold-start handling:
  Neon free tier suspends after 5 minutes of inactivity. When suspended, the
  HTTP proxy (port 443) responds immediately but port 5432 on the pooler can
  take up to 60s to come back up. _wake_neon() sends an HTTP wake request then
  polls port 5432 until available, so the first CLI run after a suspend works
  without manual retries.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

_database_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not _database_url:
    raise RuntimeError(
        "No database URL configured. Set NEON_DATABASE_URL (Neon) or DATABASE_URL."
    )


def _wake_neon(url: str) -> None:
    """
    If the Neon pooler is suspended, send an HTTP wake request then poll
    port 5432 until it accepts connections (up to 60s).

    Only called when NEON_DATABASE_URL is in use. Safe to call when Neon is
    already awake — the initial socket probe returns immediately and no HTTP
    request is made.
    """
    import re
    import urllib.parse
    import json
    import http.client
    import ssl
    import socket
    import time

    m = re.match(r"postgresql://([^:]+):([^@]+)@([^/]+)/([^?]+)", url)
    if not m:
        return
    user, pw_enc, host, db_name = m.groups()
    pw = urllib.parse.unquote(pw_enc)

    # Resolve once; reuse for polling.
    try:
        ip = socket.getaddrinfo(host, 5432, socket.AF_INET)[0][4][0]
    except Exception:
        return

    def _port_open(timeout: float = 2.0) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, 5432))
            s.close()
            return True
        except Exception:
            return False

    # Fast path: already awake.
    if _port_open():
        return

    # Send HTTP wake request via Neon's serverless proxy.
    print("Neon suspended — waking via HTTP proxy...", file=sys.stderr)
    conn_str = f"postgresql://{user}:{pw}@{host}/{db_name}?sslmode=require"
    try:
        ctx = ssl.create_default_context()
        c = http.client.HTTPSConnection(host, 443, context=ctx, timeout=30)
        c.request(
            "POST",
            "/sql",
            body=json.dumps({"query": "SELECT 1"}).encode(),
            headers={
                "Content-Type": "application/json",
                "Neon-Connection-String": conn_str,
            },
        )
        resp = c.getresponse()
        resp.read()
        c.close()
    except Exception:
        pass  # HTTP wake failed — let psycopg2 try anyway.

    # Poll port 5432 for up to 60 s.
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(3)
        if _port_open():
            print("Neon compute ready.", file=sys.stderr)
            return

    print("Neon port 5432 still starting — proceeding anyway.", file=sys.stderr)


# Wake Neon before the engine is created so the first connection succeeds.
if os.environ.get("NEON_DATABASE_URL") and _database_url == os.environ.get("NEON_DATABASE_URL"):
    _wake_neon(_database_url)

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

    Uses generate_series to call nextval n times server-side, avoiding n individual
    round trips.  Critical for bulk-inserting large atom sets (e.g. 1000-atom
    single-paragraph inputs) within the 10-second latency budget.
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

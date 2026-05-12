"""
Database session management for SysEngage.

Architectural commitment: Neon PostgreSQL via SQLAlchemy 2.x.
Per Row 4 Applied §5 — connection pool, session factory, engine configuration.

Connection priority:
  1. NEON_DATABASE_URL — external Neon project (canonical production target).
  2. DATABASE_URL      — Replit-managed Helium Postgres (dev fallback).

The Replit dev environment blocks outbound TCP port 5432 to external hosts.
A fast socket pre-check (1s timeout) detects this and falls back to
DATABASE_URL automatically, printing a clear warning. The deployed app reaches
Neon directly because Replit deployments have unrestricted outbound networking.
"""

import os
import socket
import re
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


def _neon_reachable(url: str) -> bool:
    """Return True if the host in *url* accepts a TCP connection on port 5432."""
    m = re.search(r"@([^/:]+)(?::(\d+))?/", url)
    if not m:
        return False
    host = m.group(1)
    port = int(m.group(2)) if m.group(2) else 5432
    try:
        addrs = socket.getaddrinfo(host, port, socket.AF_INET)
        ip = addrs[0][4][0]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip, port))
        s.close()
        return True
    except Exception:
        return False


_neon_url = os.environ.get("NEON_DATABASE_URL", "")
_local_url = os.environ.get("DATABASE_URL", "")

if _neon_url and _neon_reachable(_neon_url):
    _database_url = _neon_url
    _db_label = "Neon (NEON_DATABASE_URL)"
elif _neon_url and _local_url:
    print(
        "WARNING: NEON_DATABASE_URL is set but port 5432 is unreachable from this "
        "environment (Replit dev blocks outbound TCP 5432). "
        "Falling back to DATABASE_URL (Helium). "
        "The deployed app will use Neon correctly.",
        file=sys.stderr,
    )
    _database_url = _local_url
    _db_label = "Helium fallback (DATABASE_URL)"
elif _local_url:
    _database_url = _local_url
    _db_label = "Helium (DATABASE_URL)"
elif _neon_url:
    _database_url = _neon_url
    _db_label = "Neon (NEON_DATABASE_URL)"
else:
    raise RuntimeError(
        "No database URL configured. Set NEON_DATABASE_URL (Neon) or DATABASE_URL."
    )

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

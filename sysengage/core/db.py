"""
Database session management for SysEngage.

Architectural commitment: Neon PostgreSQL via SQLAlchemy 2.x.
Per Row 4 Applied §5 — connection pool, session factory, engine configuration.

Build context note: NEON_DATABASE_URL env var holds the Neon connection string.
Falls back to DATABASE_URL for Replit-managed Postgres in development.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

_database_url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not _database_url:
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

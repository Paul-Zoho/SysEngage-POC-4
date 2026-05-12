"""
Alembic environment configuration.

Per Row 4 Applied §5: all schema changes via Alembic migrations.
Never use Base.metadata.create_all() or raw schema-creating SQL directly.
"""

import os
import sys
import socket
import re
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.base import Base
import models.project  # noqa: F401 — register model
import models.stakeholder  # noqa: F401
import models.segment  # noqa: F401
import models.source  # noqa: F401
import models.source_atom  # noqa: F401
import models.analysis_pass  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


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
    _db_url = _neon_url
elif _neon_url and _local_url:
    print(
        "WARNING: NEON_DATABASE_URL unreachable (port 5432 blocked). "
        "Running migrations against DATABASE_URL (Helium) instead.",
        file=sys.stderr,
    )
    _db_url = _local_url
elif _local_url:
    _db_url = _local_url
elif _neon_url:
    _db_url = _neon_url
else:
    _db_url = ""

if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

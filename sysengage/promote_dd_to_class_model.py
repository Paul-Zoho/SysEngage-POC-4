"""
One-time migration: promote DD to names-only (F107 / v0.33).

Removes relationship entries and clears value-set attributes on canonical
entries in data_dictionary_entry.  Leaves canonical name rows and synonym
rows untouched.

Per Requirement Derivation Mechanism Spec v0.33 §12.3:

  Post-F107, the Data Dictionary is names+synonyms only.
  - Rows with entry_kind = 'relationship' are deleted.
  - Canonical rows with non-empty attributes JSONB (value-sets recorded by
    record_value() calls) have their attributes column reset to '[]'::jsonb.
  - Non-empty value-sets are logged as orphan_value_set_on_migration advisories.

Usage (run from workspace root):
    python -u sysengage/promote_dd_to_class_model.py [--dry-run]

Requires NEON_DATABASE_URL (or DATABASE_URL) to point at the target branch.
Pass --dry-run to preview counts without committing.
"""

from __future__ import annotations

import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
_log = logging.getLogger("promote_dd_to_class_model")


def _get_db_url() -> str:
    url = (
        os.environ.get("NEON_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not url:
        raise RuntimeError(
            "NEON_DATABASE_URL or DATABASE_URL must be set before running "
            "this script."
        )
    return url


def run(dry_run: bool = False) -> None:
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
    except ImportError as exc:
        _log.error("SQLAlchemy not available: %s", exc)
        sys.exit(1)

    db_url = _get_db_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with Session(engine) as session:
        # --- Count relationship entries ---
        rel_count: int = session.execute(
            text(
                "SELECT COUNT(*) FROM data_dictionary_entry "
                "WHERE entry_kind = 'relationship'"
            )
        ).scalar_one()
        _log.info("Relationship entries found: %d", rel_count)

        # --- Find canonicals with non-empty attributes JSONB ---
        value_set_rows = session.execute(
            text(
                "SELECT dd_id, name, attributes "
                "FROM data_dictionary_entry "
                "WHERE entry_kind = 'canonical' "
                "  AND attributes != '[]'::jsonb "
                "  AND retired_at IS NULL"
            )
        ).fetchall()
        _log.info(
            "Canonical entries with non-empty value-sets: %d",
            len(value_set_rows),
        )

        for dd_id, name, attrs in value_set_rows:
            try:
                attrs_str = json.dumps(attrs)[:200]
            except Exception:
                attrs_str = str(attrs)[:200]
            _log.info(
                "  orphan_value_set_on_migration: dd_id=%s name=%r attrs_preview=%s",
                dd_id,
                name,
                attrs_str,
            )

        if dry_run:
            _log.info(
                "DRY RUN — no changes committed.  Would delete %d relationship "
                "rows and clear value-set attributes on %d canonical entries.",
                rel_count,
                len(value_set_rows),
            )
            return

        # --- Delete relationship entries ---
        deleted_rels: int = session.execute(
            text(
                "DELETE FROM data_dictionary_entry WHERE entry_kind = 'relationship'"
            )
        ).rowcount
        _log.info("Deleted %d relationship entries.", deleted_rels)

        # --- Clear value-sets on canonical entries ---
        cleared: int = session.execute(
            text(
                "UPDATE data_dictionary_entry "
                "SET attributes = '[]'::jsonb "
                "WHERE entry_kind = 'canonical' "
                "  AND attributes != '[]'::jsonb"
            )
        ).rowcount
        _log.info(
            "Cleared value-set attributes on %d canonical entries.", cleared
        )

        session.commit()
        _log.info("Migration committed successfully.")

    engine.dispose()
    _log.info("Done.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        _log.info("Running in DRY-RUN mode — no DB changes will be committed.")
    run(dry_run=dry_run)

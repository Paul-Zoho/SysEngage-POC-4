"""Change zachman_cell PK from cell_id to (cell_id, project_id).

cell_id format ZC-R{row}-C-{column} is NOT globally unique — two different
projects can legitimately produce ZC-R1-C-What independently.  When PK was
single-column (cell_id only) NQPS_E2E "owned" all six Row 1 cells, and PMT_E2E
Step 2a session.get(cell_id) found them and skipped creation, leaving PMT_E2E
without its own ZachmanCell rows (VER-3b-01 FAIL).

Fix mirrors migration 007 for cell_content_item:
  1. Drop FK cell_content_item_cell_id_fkey (references old single-col PK)
  2. Drop PK zachman_cell_pkey
  3. Back-fill: insert per-project ZachmanCell rows for any CCI whose
     (cell_id, project_id) pair is not yet represented.
  4. Add composite PK (cell_id, project_id) on zachman_cell
  5. Re-add FK as composite: cell_content_item(cell_id, project_id) →
     zachman_cell(cell_id, project_id) ON DELETE CASCADE

Revision ID: 008
Revises: 007
Create Date: 2026-05-17
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "cell_content_item_cell_id_fkey", "cell_content_item", type_="foreignkey"
    )

    op.drop_constraint("zachman_cell_pkey", "zachman_cell", type_="primary")

    op.execute("""
        INSERT INTO zachman_cell (cell_id, row_target, "column", project_id, created_at)
        SELECT DISTINCT ci.cell_id, zc.row_target, zc."column", ci.project_id, NOW()
        FROM cell_content_item ci
        JOIN zachman_cell zc ON ci.cell_id = zc.cell_id
        WHERE (ci.cell_id, ci.project_id) NOT IN (
            SELECT cell_id, project_id FROM zachman_cell
        )
    """)

    op.create_primary_key(
        "zachman_cell_pkey",
        "zachman_cell",
        ["cell_id", "project_id"],
    )

    op.create_foreign_key(
        "cell_content_item_cell_id_project_id_fkey",
        "cell_content_item",
        "zachman_cell",
        ["cell_id", "project_id"],
        ["cell_id", "project_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "cell_content_item_cell_id_project_id_fkey",
        "cell_content_item",
        type_="foreignkey",
    )

    op.drop_constraint("zachman_cell_pkey", "zachman_cell", type_="primary")

    # After upgrade, zachman_cell may have one row per (cell_id, project_id) pair.
    # Restoring a single-column PK on cell_id requires deduplication first — keep
    # the lexicographically first project_id row for each cell_id.
    op.execute("""
        DELETE FROM zachman_cell
        WHERE (cell_id, project_id) NOT IN (
            SELECT cell_id, MIN(project_id)
            FROM zachman_cell
            GROUP BY cell_id
        )
    """)

    op.create_primary_key(
        "zachman_cell_pkey",
        "zachman_cell",
        ["cell_id"],
    )

    op.create_foreign_key(
        "cell_content_item_cell_id_fkey",
        "cell_content_item",
        "zachman_cell",
        ["cell_id"],
        ["cell_id"],
        ondelete="CASCADE",
    )

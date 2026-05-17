"""Change cell_content_item PK from ci_id to (ci_id, project_id).

ci_id format CCI-ROW{row}-C-{col}-{seq} is scoped per cell, not globally
unique across projects.  Two different projects can legitimately produce
CCI-ROW1-C-What-001 independently.  Making (ci_id, project_id) the composite
primary key enforces per-project uniqueness without requiring a format change.

Revision ID: 007
Revises: 006
Create Date: 2026-05-17
"""

from typing import Sequence, Union
from alembic import op


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("cell_content_item_pkey", "cell_content_item", type_="primary")
    op.create_primary_key(
        "cell_content_item_pkey",
        "cell_content_item",
        ["ci_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_constraint("cell_content_item_pkey", "cell_content_item", type_="primary")
    op.create_primary_key(
        "cell_content_item_pkey",
        "cell_content_item",
        ["ci_id"],
    )

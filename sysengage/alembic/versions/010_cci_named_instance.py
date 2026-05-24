"""Add is_named_instance to cell_content_item.

Per CCI Construction Mechanism Spec v0.9 §4.3 Rule 5: the AI flags each CCI
in a named-instance group with is_named_instance=true.  This column persists
that flag to the ledger so the bypass logic in Stage 4b and downstream analysis
can inspect it without re-running the AI.

Nullable (rather than NOT NULL DEFAULT false) so that legacy rows committed
before this migration read as NULL (unknown) rather than false (explicitly not
a named instance) — the distinction matters for audit integrity.

Revision ID: 010
Revises: 009
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cell_content_item",
        sa.Column(
            "is_named_instance",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("cell_content_item", "is_named_instance")

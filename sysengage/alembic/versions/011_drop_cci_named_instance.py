"""Drop is_named_instance from cell_content_item.

The is_named_instance column was added in migration 010 to persist the AI-driven
named-instance flag from spec v0.9.  In spec v0.11, this flag is replaced by the
deterministic Stage 4a routing context (stage4a_routed marker on the in-memory
CandidateCCI struct).  The flag is never persisted — Stage 4b uses named-instance
framing when any candidate in a group carries stage4a_routed=True, determined
algorithmically by Stage 4a.  The column is now dead schema and is dropped here.

Revision ID: 011
Revises: 010
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("cell_content_item", "is_named_instance")


def downgrade() -> None:
    op.add_column(
        "cell_content_item",
        sa.Column(
            "is_named_instance",
            sa.Boolean(),
            nullable=True,
        ),
    )

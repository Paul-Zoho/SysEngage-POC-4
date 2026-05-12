"""Add segment.source_refs; drop source.segment_id FK and column.

Per canonical ledger spec v2.11, F24 fix:
  - Segment groups Sources by listing their IDs in source_refs (ARRAY of source_id).
  - Source has NO back-reference FK to Segment (segment_id column removed).

These changes exist in the ORM models but were missing from the initial migration.
This migration brings the Helium DB schema fully in sync with current models.

Revision ID: 003
Revises: 002
Create Date: 2026-05-12
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source_refs ARRAY column to segment
    op.add_column(
        "segment",
        sa.Column(
            "source_refs",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    # Drop the segment_id FK and column from source (F24 fix)
    op.drop_constraint("source_segment_id_fkey", "source", type_="foreignkey")
    op.drop_column("source", "segment_id")


def downgrade() -> None:
    op.add_column(
        "source",
        sa.Column(
            "segment_id",
            sa.String(),
            sa.ForeignKey("segment.segment_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.drop_column("segment", "source_refs")

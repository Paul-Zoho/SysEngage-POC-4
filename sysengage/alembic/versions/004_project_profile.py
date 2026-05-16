"""Add project_profile table.

Per Row-Lens Source Re-Analysis spec v0.1 §3.2:
  Separate project_profile table, one-to-one with project.
  Holds per-project configuration for AI-involving mechanisms.

Columns:
  concern_threshold (float, default 0.65) — T1 for Signal/Concern classification
  chunk_match_threshold (float, default 0.6) — Stage 1 fuzzy match threshold
  residual_batch_size (int, default 50) — AI invocation batch size for residuals

Revision ID: 004
Revises: 003
Create Date: 2026-05-16
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_profile",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "concern_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.65",
        ),
        sa.Column(
            "chunk_match_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.6",
        ),
        sa.Column(
            "residual_batch_size",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("project_profile")

"""Add stage4a_similarity_threshold to project_profile.

Per CCI Construction Mechanism Spec v0.8 §3.2: Stage 4a gains a third
auto-merge condition — Jaccard description similarity >= threshold.
The threshold is stored per-project in ProjectProfile so it can be
calibrated independently per project as empirical data accumulates.

Default 0.60 matches the spec default.  Existing rows receive the
default via the column DEFAULT — no data backfill is required.

Revision ID: 009
Revises: 008
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_profile",
        sa.Column(
            "stage4a_similarity_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.60",
        ),
    )


def downgrade() -> None:
    op.drop_column("project_profile", "stage4a_similarity_threshold")

"""018 — Add Pass 3d requirement derivation parameters to project_profile.

Per Requirement Derivation Mechanism Spec v0.1 §14.2 (Understanding v0.25):
  requirement_rerun_threshold                  FLOAT   NULL (default 0.20)
  requirement_large_cci_set_advisory_threshold INTEGER NULL (default 80)

Both are nullable — NULL means "use default". The mechanism substitutes the
documented default when the column is NULL.
"""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_profile",
        sa.Column(
            "requirement_rerun_threshold",
            sa.Float(),
            nullable=True,
        ),
    )
    op.add_column(
        "project_profile",
        sa.Column(
            "requirement_large_cci_set_advisory_threshold",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("project_profile", "requirement_large_cci_set_advisory_threshold")
    op.drop_column("project_profile", "requirement_rerun_threshold")

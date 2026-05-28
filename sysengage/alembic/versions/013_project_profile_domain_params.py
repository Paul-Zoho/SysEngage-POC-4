"""013 — Add Pass 3c domain derivation parameters to project_profile.

Per Domain Derivation Mechanism Spec v0.13 §13.9 (Understanding v0.17):
  domain_rerun_threshold               FLOAT    NULL (default 0.20)
  domain_cross_cutting_advisory_threshold INTEGER NULL (default 3)
  domain_large_cci_set_advisory_threshold INTEGER NULL (default 80)

All three are nullable — NULL means "use default". The mechanism reads the value
and substitutes the documented default if NULL.
"""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_profile",
        sa.Column(
            "domain_rerun_threshold",
            sa.Float(),
            nullable=True,
        ),
    )
    op.add_column(
        "project_profile",
        sa.Column(
            "domain_cross_cutting_advisory_threshold",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "project_profile",
        sa.Column(
            "domain_large_cci_set_advisory_threshold",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("project_profile", "domain_large_cci_set_advisory_threshold")
    op.drop_column("project_profile", "domain_cross_cutting_advisory_threshold")
    op.drop_column("project_profile", "domain_rerun_threshold")

"""023 — Add project_id to requirement_matching_log and requirement_gap_record.

requirement_id values are project-scoped (each project independently generates
R001, R002, …). Without project_id the matching-log JOIN on requirement_id alone
is ambiguous across projects and causes false-positive idempotency hits.

Realises: Requirement Matching Service v0.1 §5.2 (data-integrity fix)
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "requirement_matching_log",
        sa.Column("project_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "requirement_gap_record",
        sa.Column("project_id", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("requirement_gap_record", "project_id")
    op.drop_column("requirement_matching_log", "project_id")

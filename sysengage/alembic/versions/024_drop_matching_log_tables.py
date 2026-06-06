"""024 — Drop v0.1 Requirement Matching service-log tables.

D-rm-4 reversed in Requirement Matching Service Spec v0.2:
  requirement_matching_log  — per-requirement audit rows  ← abolished
  requirement_gap_record    — gap rows                    ← abolished

Both are replaced by a single per-execution AnalysisPass
(mechanism='RequirementMatching') whose outputs.mechanism_data carries
match_records and gap_records in the ledger, on the same review path as
every other mechanism's provenance.

The requirement_quality_result table (also from migration 021) is NOT
dropped — it belongs to the Requirement Quality Analysis service which
retains its own storage model.
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("requirement_matching_log")
    op.drop_table("requirement_gap_record")


def downgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    op.create_table(
        "requirement_gap_record",
        sa.Column("gap_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("project_id", sa.String(32), nullable=True),
        sa.Column("row_target", sa.String(1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint("direction IN ('upward','downward')", name="ck_gap_direction"),
        sa.PrimaryKeyConstraint("gap_id"),
    )
    op.create_table(
        "requirement_matching_log",
        sa.Column("log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("project_id", sa.String(32), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("parent_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("duplicate_of", sa.String(8), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("auto_recorded", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('refine','duplicate','no_match','flagged','deferred')",
            name="ck_rm_log_outcome",
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )

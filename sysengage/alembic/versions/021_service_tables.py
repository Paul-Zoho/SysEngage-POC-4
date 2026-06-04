"""021 — Service tables: Requirement Matching and Quality Analysis.

Creates three new side-table records written by the cross-row services:

  requirement_matching_log     — per-requirement matching audit (D-rm-4; not
                                  an AnalysisPass — high-frequency per-requirement).
                                  outcome ∈ refine|duplicate|no_match|flagged|deferred.

  requirement_gap_record       — upward (child-orphan, no refines_refs) and downward
                                  (parent-orphan, no row-below refinement) gaps surfaced
                                  for GQA consumption (F86/F84).

  requirement_quality_result   — per-requirement quality score from Phase 4 RQA (D-q-4;
                                  side table, not a canonical ledger element at this version).
                                  Latest result per requirement supersedes on re-score.

None of these are canonical ledger element types; they are analysis output records.
Gap records and quality results may promote to canonical elements in later versions.

Realises:
  Row 4 Requirement Matching Service v0.1 §5.2
  Row 4 Requirement Quality Analysis v0.1 §5.2
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_matching_log",
        sa.Column("log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column(
            "parent_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
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

    op.create_table(
        "requirement_gap_record",
        sa.Column("gap_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("row_target", sa.String(1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('upward','downward')",
            name="ck_gap_direction",
        ),
        sa.PrimaryKeyConstraint("gap_id"),
    )

    op.create_table(
        "requirement_quality_result",
        sa.Column("result_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("effective_type", sa.String(16), nullable=False),
        sa.Column("reclassified_from", sa.String(16), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "violations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "effective_type IN ('Functional','Constraint','Structural')",
            name="ck_rqr_effective_type",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_rqr_score_range",
        ),
        sa.PrimaryKeyConstraint("result_id"),
    )


def downgrade() -> None:
    op.drop_table("requirement_quality_result")
    op.drop_table("requirement_gap_record")
    op.drop_table("requirement_matching_log")

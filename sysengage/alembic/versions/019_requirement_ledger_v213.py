"""019 — Requirement table: ledger v2.13 changes.

Three changes per spec (Row 4 Requirement Derivation v0.5, ledger v2.13):

  1. requirement_type CHECK: collapse 5-value enum (Functional/Constraint/
     Performance/Suitability/Non-Functional) → 3-value triad
     (Functional/Constraint/Structural). Finding F89.

  2. verification_method CHECK: add 'Measurement' to the allowed set.
     (Replaces the Performance-fit-criteria rule with Measurement-fit-criteria.)

  3. refines_refs JSONB column: added NOT NULL DEFAULT '[]'. Populated later by
     the Requirement Matching service (F82/F85); Pass 3d always writes [].

Existing rows with legacy requirement_type values (Performance, Suitability,
Non-Functional) are migrated in migration 022 immediately after. PostgreSQL does
NOT retroactively validate existing rows when a CHECK is dropped and recreated,
so the order is: schema change (019) → data migration (022).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Collapse requirement_type CHECK to three-value triad
    op.drop_constraint("ck_requirement_type", "requirement", type_="check")
    op.create_check_constraint(
        "ck_requirement_type",
        "requirement",
        "requirement_type IN ('Functional','Constraint','Structural')",
    )

    # 2. Add Measurement to verification_method
    op.drop_constraint("ck_requirement_verification_method", "requirement", type_="check")
    op.create_check_constraint(
        "ck_requirement_verification_method",
        "requirement",
        "verification_method IS NULL OR verification_method IN "
        "('Test','Analysis','Inspection','Demonstration','Measurement')",
    )

    # 3. Add refines_refs — empty array at construction; Matching service populates it
    op.add_column(
        "requirement",
        sa.Column(
            "refines_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("requirement", "refines_refs")

    op.drop_constraint("ck_requirement_verification_method", "requirement", type_="check")
    op.create_check_constraint(
        "ck_requirement_verification_method",
        "requirement",
        "verification_method IS NULL OR verification_method IN "
        "('Test','Analysis','Inspection','Demonstration')",
    )

    op.drop_constraint("ck_requirement_type", "requirement", type_="check")
    op.create_check_constraint(
        "ck_requirement_type",
        "requirement",
        "requirement_type IN ('Functional','Constraint','Performance','Suitability','Non-Functional')",
    )

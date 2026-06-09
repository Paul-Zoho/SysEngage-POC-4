"""025 — Relax ck_requirement_cci_refs_nonempty for Path R

Path R proposals (RD v0.13) legitimately have cci_refs = [] at derivation
time; their cci_refs are populated later by the Requirement Matching service.
The original constraint (jsonb_array_length(cci_refs) >= 1) was correct before
Path R existed but now conflicts with the relaxed CHK-3d-02 rule:

  A requirement must have EITHER cci_refs non-empty OR refines_refs non-empty.

This migration drops the old constraint and recreates it with the OR clause.
"""

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_requirement_cci_refs_nonempty",
        "requirement",
        type_="check",
    )
    op.create_check_constraint(
        "ck_requirement_cci_refs_nonempty",
        "requirement",
        "jsonb_array_length(cci_refs) >= 1 OR jsonb_array_length(refines_refs) >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_requirement_cci_refs_nonempty",
        "requirement",
        type_="check",
    )
    op.create_check_constraint(
        "ck_requirement_cci_refs_nonempty",
        "requirement",
        "jsonb_array_length(cci_refs) >= 1",
    )

"""022 — Data migration: requirement_type 5-value → 3-value triad.

Migration 019 changed the CHECK constraint to accept only the three-value triad
(Functional / Constraint / Structural). This migration updates any existing rows
that carry the five legacy values:

  Performance  → Constraint  (a quantified constraint on resource or timing;
                               verified by Measurement per v2.13 rule)
  Suitability  → Constraint  (a qualitative fit-for-purpose rule; Inspection-verified)
  Non-Functional → Structural (a composition/relationship/architectural statement)

Rationale (ledger v2.13 Appendix D; Row 4 Requirement Derivation v0.5 §12.8):
  The five-value enum pre-dates the F89 type-triad design decision. Performance
  and Suitability are both Constraint subtypes distinguished only by their
  verification_method (Measurement vs Inspection); collapsing them to Constraint
  requires no information loss beyond that distinction, which is carried on the
  verification_method column. Non-Functional was a catch-all for structural and
  architectural obligations; Structural is the correct triad slot.

Downgrade: the original distinction between Performance and Suitability (and
the specific reason a row was Non-Functional) is not recoverable from the data
alone — downgrade is a no-op with a warning. Restore from a pre-019 snapshot
if a full rollback is required.
"""

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Performance → Constraint
    conn.execute(
        sa.text(
            "UPDATE requirement "
            "SET requirement_type = 'Constraint' "
            "WHERE requirement_type = 'Performance'"
        )
    )

    # Suitability → Constraint
    conn.execute(
        sa.text(
            "UPDATE requirement "
            "SET requirement_type = 'Constraint' "
            "WHERE requirement_type = 'Suitability'"
        )
    )

    # Non-Functional → Structural
    conn.execute(
        sa.text(
            "UPDATE requirement "
            "SET requirement_type = 'Structural' "
            "WHERE requirement_type = 'Non-Functional'"
        )
    )


def downgrade() -> None:
    # The original Performance/Suitability/Non-Functional distinctions are not
    # recoverable from the migrated data. Downgrade is intentionally a no-op.
    # To restore legacy values, roll back to a snapshot taken before migration 019.
    pass

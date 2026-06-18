"""026 — Add class_model and object_refs columns to requirement

F105: class_model (JSONB NULL) — holds the structured class model for Structural
      requirements. NULL for Functional and Constraint types.
      CHECK: class_model IS NULL OR requirement_type = 'Structural'

F107: object_refs (JSONB NOT NULL DEFAULT '[]') — holds materialised object-reference
      paths for behavioural (Functional/Constraint) requirements.
      CHECK: requirement_type IN ('Functional','Constraint') OR jsonb_array_length(object_refs) = 0

Per Requirement Derivation Mechanism Spec v0.33 §5.1.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("requirement", sa.Column("class_model", JSONB, nullable=True))
    op.add_column(
        "requirement",
        sa.Column(
            "object_refs",
            JSONB,
            nullable=False,
            server_default="'[]'::jsonb",
        ),
    )
    op.create_check_constraint(
        "ck_requirement_class_model_structural_only",
        "requirement",
        "class_model IS NULL OR requirement_type = 'Structural'",
    )
    op.create_check_constraint(
        "ck_requirement_object_refs_behavioural_only",
        "requirement",
        "requirement_type IN ('Functional','Constraint') OR jsonb_array_length(object_refs) = 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_requirement_object_refs_behavioural_only", "requirement", type_="check"
    )
    op.drop_constraint(
        "ck_requirement_class_model_structural_only", "requirement", type_="check"
    )
    op.drop_column("requirement", "object_refs")
    op.drop_column("requirement", "class_model")

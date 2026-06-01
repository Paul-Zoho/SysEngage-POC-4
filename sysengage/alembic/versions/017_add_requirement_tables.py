"""017 — Replace requirement stub with full Pass 3d schema.

Drops the lightweight requirement stub from migration 012 (which had a direct
domain_id FK) and creates the full Pass 3d Requirement table per Mechanism Spec
v0.1 §5.1:

  requirement       — composite PK (requirement_id, project_id); JSONB cci_refs,
                      domain_refs, answer_refs; requirement_type enum;
                      confidence; retired_at soft-delete; optional text fields.

RequirementRegister rows are NOT seeded here — projects do not exist at
migration time. ensure_requirement_register_seeded() in core/ledger.py seeds
the register per-project before the first Pass 3d run, exactly as
ensure_domain_register_seeded() does for the DomainRegister.

The register table already exists (created in migration 012).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the stub requirement table (FK to domain composite PK)
    op.drop_table("requirement")

    # Full Pass 3d requirement table
    op.create_table(
        "requirement",
        sa.Column("requirement_id", sa.String(8), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("requirement_type", sa.String(16), nullable=False),
        sa.Column("row_target", sa.String(1), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "cci_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "domain_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("fit_criteria", sa.Text(), nullable=True),
        sa.Column("verification_method", sa.String(16), nullable=True),
        sa.Column("priority", sa.String(8), nullable=True),
        sa.Column(
            "answer_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            r"requirement_id ~ '^R\d{3}$'",
            name="ck_requirement_id_format",
        ),
        sa.CheckConstraint(
            "length(statement) > 0",
            name="ck_requirement_statement_nonempty",
        ),
        sa.CheckConstraint(
            "requirement_type IN ('Functional','Constraint','Performance','Suitability','Non-Functional')",
            name="ck_requirement_type",
        ),
        sa.CheckConstraint(
            "row_target IN ('1','2','3','4','5','6')",
            name="ck_requirement_row_target",
        ),
        sa.CheckConstraint(
            "jsonb_array_length(cci_refs) >= 1",
            name="ck_requirement_cci_refs_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_array_length(domain_refs) >= 1",
            name="ck_requirement_domain_refs_nonempty",
        ),
        sa.CheckConstraint(
            "fit_criteria IS NULL OR length(fit_criteria) > 0",
            name="ck_requirement_fit_criteria",
        ),
        sa.CheckConstraint(
            "verification_method IS NULL OR verification_method IN ('Test','Analysis','Inspection','Demonstration')",
            name="ck_requirement_verification_method",
        ),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN ('High','Medium','Low')",
            name="ck_requirement_priority",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_requirement_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="requirement_project_id_fkey",
        ),
        sa.PrimaryKeyConstraint("requirement_id", "project_id"),
    )


def downgrade() -> None:
    op.drop_table("requirement")

    # Restore the migration 012 stub
    op.create_table(
        "requirement",
        sa.Column("requirement_id", sa.String(), nullable=False),
        sa.Column("statement", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(10), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["domain_id", "project_id"],
            ["domain.domain_id", "domain.project_id"],
            name="requirement_domain_composite_fk",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="requirement_project_id_fkey",
        ),
        sa.PrimaryKeyConstraint("requirement_id"),
    )

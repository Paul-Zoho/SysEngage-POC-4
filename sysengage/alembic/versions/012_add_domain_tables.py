"""012 — Add domain tables (composite PK), domain_cci_membership, register table.

Replaces the domain stub from migration 005 with the full Pass 3c schema per
Domain Derivation Mechanism Spec v0.13 §5.1:

  register                — per-project element registers; DomainRegister rows
                            seeded at run time by ensure_domain_register_seeded()
  domain                  — composite PK (domain_id, project_id), description,
                            classification_type, retired_at, CHECK constraints
  domain_cci_membership   — join table for Domain ↔ CCI membership (FK integrity)

Also updates requirement stub to use the composite FK on domain.

Note: no DomainRegister INSERT here — projects do not exist at migration time.
DomainRegister is seeded per-project by ensure_domain_register_seeded() in
core/ledger.py, called from Stage 1 pre-flight.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop requirement first (has FK to domain)
    op.drop_table("requirement")
    # Drop old domain stub (simple PK, no description/retired_at)
    op.drop_table("domain")

    # register table — general per-project element registers
    op.create_table(
        "register",
        sa.Column("register_id", sa.String(50), nullable=False),
        sa.Column("register_type", sa.String(50), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column(
            "member_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("completeness_rule", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="register_project_id_fkey",
        ),
        sa.PrimaryKeyConstraint("register_id", "project_id"),
    )

    # domain table — full Pass 3c schema
    op.create_table(
        "domain",
        sa.Column("domain_id", sa.String(10), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("classification_type", sa.Text(), nullable=True),
        sa.Column("row_target", sa.String(1), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            r"domain_id ~ '^D\d{3}$'",
            name="ck_domain_id_format",
        ),
        sa.CheckConstraint(
            "row_target IN ('1','2','3','4','5','6')",
            name="ck_domain_row_target",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="domain_project_id_fkey",
        ),
        sa.PrimaryKeyConstraint("domain_id", "project_id"),
    )

    # domain_cci_membership join table
    op.create_table(
        "domain_cci_membership",
        sa.Column("domain_id", sa.String(10), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("ci_id", sa.String(60), nullable=False),
        sa.ForeignKeyConstraint(
            ["domain_id", "project_id"],
            ["domain.domain_id", "domain.project_id"],
            name="dcm_domain_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ci_id", "project_id"],
            ["cell_content_item.ci_id", "cell_content_item.project_id"],
            name="dcm_cci_fkey",
        ),
        sa.PrimaryKeyConstraint("domain_id", "project_id", "ci_id"),
    )

    # requirement stub — updated with composite FK on domain
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


def downgrade() -> None:
    op.drop_table("requirement")
    op.drop_table("domain_cci_membership")
    op.drop_table("domain")
    op.drop_table("register")

    # Restore domain stub
    op.create_table(
        "domain",
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("domain_id"),
    )

    # Restore requirement stub with simple FK
    op.create_table(
        "requirement",
        sa.Column("requirement_id", sa.String(), nullable=False),
        sa.Column("statement", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["domain_id"], ["domain.domain_id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("requirement_id"),
    )

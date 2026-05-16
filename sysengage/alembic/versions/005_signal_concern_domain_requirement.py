"""Add sg_id_seq, cn_id_seq, signal, concern, domain, requirement tables.

Per Row-Lens Source Re-Analysis spec v0.1 §5.2, §5.3:
  - sg_id_seq — Postgres sequence for Signal identifiers (SG###)
  - cn_id_seq — Postgres sequence for Concern identifiers (CN###, no hyphen)
  - signal table — canonical Signal entity per ledger spec v2.12
  - concern table — canonical Concern entity per ledger spec v2.12
  - domain table — minimal stub for Phase 3 Pass 3a reading (Stage 1)
  - requirement table — minimal stub for Phase 3 Pass 3a reading (Stage 1)

Signal: source_refs and sourceatom_refs stored as JSONB arrays.
Concern: source_refs stored as JSONB array.

Revision ID: 005
Revises: 004
Create Date: 2026-05-16
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Sequences for new canonical identifier types ---
    op.execute("CREATE SEQUENCE IF NOT EXISTS sg_id_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS cn_id_seq START 1")

    # --- domain table (stub for Phase 3 Pass 3a reading) ---
    op.create_table(
        "domain",
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("domain_id"),
    )

    # --- requirement table (stub for Phase 3 Pass 3a reading) ---
    op.create_table(
        "requirement",
        sa.Column("requirement_id", sa.String(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("domain_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"], ["domain.domain_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("requirement_id"),
    )

    # --- signal table ---
    op.create_table(
        "signal",
        sa.Column("signal_id", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "sourceatom_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("derived_from_concern_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            r"signal_id ~ '^SG\d{3,}$'", name="ck_signal_id_format"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("signal_id"),
    )

    # --- concern table ---
    op.create_table(
        "concern",
        sa.Column("concern_id", sa.String(), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="Open"),
        sa.Column("produced_in_row", sa.String(), nullable=False),
        sa.Column("practitioner_id", sa.String(), nullable=False),
        sa.Column("dispositioned_with_outcome", sa.String(), nullable=True),
        sa.Column("disposition_rationale", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            r"concern_id ~ '^CN\d{3,}$'", name="ck_concern_id_format"
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["stakeholder.stakeholder_id"]
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("concern_id"),
    )


def downgrade() -> None:
    op.drop_table("concern")
    op.drop_table("signal")
    op.drop_table("requirement")
    op.drop_table("domain")
    op.execute("DROP SEQUENCE IF EXISTS cn_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS sg_id_seq")

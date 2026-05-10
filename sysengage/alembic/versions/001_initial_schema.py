"""Initial schema — project, stakeholder, segment, source, source_atom, analysis_pass.

Per Row 4 Applied §5:
- Postgres sequences per identifier prefix (s_id_seq, seg_id_seq, sa_id_seq, p_id_seq).
- Identifier format: prefix + zero-padded to 3 digits minimum (S001, SEG001, SA001, P001).
- Sequence-based identifier: 'S' || to_char(nextval('s_id_seq'), 'FM000')
  FM000 produces minimum 3 digits, extends for larger numbers (S1000, S10000, etc.).
- Foreign keys with appropriate cascade rules per Implementation Spec §5.5.
- JSONB outputs column on analysis_pass (JSON in SQLAlchemy maps to JSONB in Postgres).

Finding F18 applied: canonical identifier patterns from ledger spec v2.9.

Revision ID: 001
Revises: None
Create Date: 2026-05-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Postgres sequences for canonical identifier generation ---
    # Per Row 4 Applied §5 and Implementation Spec §5.4.
    # Naming: {prefix}_id_seq (lowercase prefix of identifier type).
    op.execute("CREATE SEQUENCE IF NOT EXISTS s_id_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS seg_id_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS sa_id_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS p_id_seq START 1")

    # --- project table ---
    op.create_table(
        "project",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )

    # --- stakeholder table ---
    op.create_table(
        "stakeholder",
        sa.Column("stakeholder_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("stakeholder_type", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("stakeholder_id"),
    )

    # --- segment table ---
    op.create_table(
        "segment",
        sa.Column("segment_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_segment_ref", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_segment_ref"],
            ["segment.segment_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
        ),
        sa.PrimaryKeyConstraint("segment_id"),
    )

    # --- source table ---
    op.create_table(
        "source",
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("segmentation_context", sa.String(), nullable=False),
        sa.Column("parent_source_ref", sa.String(), nullable=True),
        sa.Column("input_material_ref", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("segment_id", sa.String(), nullable=True),
        sa.Column("is_non_text", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "has_decoding_issues", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_source_ref"], ["source.source_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"], ["segment.segment_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("source_id"),
    )

    # --- source_atom table ---
    op.create_table(
        "source_atom",
        sa.Column("atom_id", sa.String(), nullable=False),
        sa.Column("atom_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("segment_ref", sa.String(), nullable=True),
        sa.Column("parent_atom_ref", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["source_ref"], ["source.source_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["segment_ref"], ["segment.segment_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["parent_atom_ref"], ["source_atom.atom_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("atom_id"),
    )

    # --- analysis_pass table ---
    op.create_table(
        "analysis_pass",
        sa.Column("pass_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False, server_default="PH001"),
        sa.Column("pass_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pass_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_status", sa.String(), nullable=False),
        sa.Column("mode_active", sa.String(), nullable=False, server_default="LPM"),
        sa.Column(
            "declared_transformation_modes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["LPM"]',
        ),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("practitioner_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "outputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["stakeholder.stakeholder_id"]
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("pass_id"),
    )

    # --- seed SH001 reserved SysEngage Tool Stakeholder ---
    # Per canonical ledger spec v2.9: "Contain the reserved SH001 SysEngage Tool Stakeholder"
    op.execute(
        """
        INSERT INTO stakeholder (stakeholder_id, name, stakeholder_type)
        VALUES ('SH001', 'SysEngage Tool', 'system')
        ON CONFLICT (stakeholder_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("analysis_pass")
    op.drop_table("source_atom")
    op.drop_table("source")
    op.drop_table("segment")
    op.drop_table("stakeholder")
    op.drop_table("project")
    op.execute("DROP SEQUENCE IF EXISTS p_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS sa_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS seg_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS s_id_seq")

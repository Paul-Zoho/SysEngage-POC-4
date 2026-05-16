"""Add zachman_cell, cell_content_item tables; extend project_profile.

Per CCI Construction Mechanism Spec v0.2:
  - zachman_cell: six cells per row (ZC-R{row}-C-{column}), upserted on every
    Pass 3b run.
  - cell_content_item: CCI entities (CCI-ROW{row}-C-{column}-{seq}), one per
    distinct classified content item per cell, sequence scoped per cell.
  - project_profile gains cci_consolidation_threshold (default 0.80) and
    cci_batch_size (default 20) per spec §3.3.

Revision ID: 006
Revises: 005
Create Date: 2026-05-16
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extend project_profile with CCI Construction config params ---
    op.add_column(
        "project_profile",
        sa.Column(
            "cci_consolidation_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.80",
        ),
    )
    op.add_column(
        "project_profile",
        sa.Column(
            "cci_batch_size",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
    )

    # --- zachman_cell table ---
    op.create_table(
        "zachman_cell",
        sa.Column("cell_id", sa.String(), nullable=False),
        sa.Column("row_target", sa.String(), nullable=False),
        sa.Column("column", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            r"cell_id ~ '^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$'",
            name="ck_zachman_cell_id_format",
        ),
        sa.CheckConstraint(
            '"column" IN (\'What\',\'How\',\'Where\',\'Who\',\'When\',\'Why\')',
            name="ck_zachman_cell_column",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("cell_id"),
    )

    # --- cell_content_item table ---
    op.create_table(
        "cell_content_item",
        sa.Column("ci_id", sa.String(), nullable=False),
        sa.Column("cell_id", sa.String(), nullable=False),
        sa.Column("classification_type", sa.String(), nullable=False),
        sa.Column(
            "signal_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("trigger_condition", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            r"ci_id ~ '^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$'",
            name="ck_cci_id_format",
        ),
        sa.ForeignKeyConstraint(
            ["cell_id"], ["zachman_cell.cell_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.project_id"]),
        sa.PrimaryKeyConstraint("ci_id"),
    )


def downgrade() -> None:
    op.drop_table("cell_content_item")
    op.drop_table("zachman_cell")
    op.drop_column("project_profile", "cci_batch_size")
    op.drop_column("project_profile", "cci_consolidation_threshold")

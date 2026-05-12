"""Add pass_type, mechanism, evaluated_scope, confidence to analysis_pass.

Per canonical ledger spec v2.11, F25/F27 resolution:
  pass_type, mechanism, evaluated_scope, confidence added as dedicated columns
  so they can be queried independently and included in canonical export.

These columns exist in the ORM model (analysis_pass.py) but were missing from
the initial migration (001). This migration brings the Helium DB schema in sync.

Revision ID: 002
Revises: 001
Create Date: 2026-05-12
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_pass",
        sa.Column(
            "pass_type",
            sa.String(),
            nullable=False,
            server_default="Universal",
        ),
    )
    op.add_column(
        "analysis_pass",
        sa.Column(
            "mechanism",
            sa.String(),
            nullable=False,
            server_default="SourceCapture",
        ),
    )
    op.add_column(
        "analysis_pass",
        sa.Column(
            "evaluated_scope",
            sa.String(),
            nullable=False,
            server_default="All input material in this project",
        ),
    )
    op.add_column(
        "analysis_pass",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_pass", "confidence")
    op.drop_column("analysis_pass", "evaluated_scope")
    op.drop_column("analysis_pass", "mechanism")
    op.drop_column("analysis_pass", "pass_type")

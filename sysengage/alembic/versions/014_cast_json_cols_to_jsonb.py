"""014 — Cast json columns to jsonb on analysis_pass.

The initial schema created outputs and declared_transformation_modes as plain
json instead of jsonb.  JSONB subscript notation (used by Stage 1 preflight
queries) only works on jsonb; plain json raises DatatypeMismatch.

Safe USING cast: json → jsonb is lossless.
"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE analysis_pass "
        "ALTER COLUMN outputs TYPE jsonb USING outputs::jsonb"
    )
    op.execute(
        "ALTER TABLE analysis_pass "
        "ALTER COLUMN declared_transformation_modes "
        "TYPE jsonb USING declared_transformation_modes::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE analysis_pass "
        "ALTER COLUMN outputs TYPE json USING outputs::json"
    )
    op.execute(
        "ALTER TABLE analysis_pass "
        "ALTER COLUMN declared_transformation_modes "
        "TYPE json USING declared_transformation_modes::json"
    )

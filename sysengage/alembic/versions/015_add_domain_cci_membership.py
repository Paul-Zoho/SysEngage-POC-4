"""015 — Add domain_cci_membership table (IF NOT EXISTS).

Migration 012 was stamped on some branches before the domain_cci_membership
CREATE TABLE block was added to that file, so the table is absent on those
branches while alembic_version already shows 012.  This migration creates it
idempotently so it is safe to run on any branch regardless of whether the
table already exists.
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_cci_membership (
            domain_id  VARCHAR(10)  NOT NULL,
            project_id VARCHAR(50)  NOT NULL,
            ci_id      VARCHAR(60)  NOT NULL,
            CONSTRAINT domain_cci_membership_pkey
                PRIMARY KEY (domain_id, project_id, ci_id),
            CONSTRAINT dcm_domain_fkey
                FOREIGN KEY (domain_id, project_id)
                REFERENCES domain (domain_id, project_id)
                ON DELETE CASCADE,
            CONSTRAINT dcm_cci_fkey
                FOREIGN KEY (ci_id, project_id)
                REFERENCES cell_content_item (ci_id, project_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS domain_cci_membership")

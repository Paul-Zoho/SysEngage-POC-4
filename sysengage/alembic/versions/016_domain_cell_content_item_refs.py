"""016 — Replace domain_cci_membership with cell_content_item_refs JSONB column.

Per Domain Derivation Mechanism Spec v0.14 §5.1 (MD-4):
  The canonical ledger v2.12 Domain schema defines cell_content_item_refs as a
  string[] attribute directly on the Domain entity.  The previous implementation
  stored this as a separate domain_cci_membership join table, which caused
  cell_content_item_refs to be absent from exported canonical payloads.

Changes:
  1. DROP TABLE domain_cci_membership (IF EXISTS — migration 015 may have
     created it on some branches; using IF EXISTS is safe on all branches)
  2. ALTER TABLE domain ADD COLUMN cell_content_item_refs JSONB NOT NULL
     DEFAULT '[]'
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS domain_cci_membership")
    op.add_column(
        "domain",
        sa.Column(
            "cell_content_item_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("domain", "cell_content_item_refs")
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

"""020 — Data Dictionary tables: ledger v2.14.

Creates the two new element types introduced by ledger v2.14:

  data_dictionary_entry       — DD### elements; entry_kind discriminates
                                canonical / synonym / relationship variants.
                                Self-referential FKs for resolves_to, from_ref,
                                to_ref (all pointing at canonical entries).
                                Conditional requireds enforced at app layer
                                (CHECKs cover structural invariants).

  data_dictionary_resolution_log — per-term resolution audit trail (D-dd-4).
                                   NOT an AnalysisPass — high-frequency,
                                   per-term.

The DataDictionaryRegister is a row in the existing 'register' table seeded
at run time by ensure_dd_register_seeded() (same pattern as DomainRegister and
RequirementRegister). No INSERT here — projects do not exist at migration time.

No project_id column: the DD is project-wide (v2.14 §3). The dd_id sequence
is managed by the application (DD### format, ^DD\\d{3}$).

Realises: Row 4 Data Dictionary Service v0.1 §5.1, ledger v2.14.
"""

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_dictionary_entry",
        sa.Column("dd_id", sa.String(8), nullable=False),
        sa.Column(
            "entry_kind",
            sa.String(16),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "attributes",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("surface_term", sa.Text(), nullable=True),
        sa.Column("resolves_to", sa.String(8), nullable=True),
        sa.Column("from_ref", sa.String(8), nullable=True),
        sa.Column("to_ref", sa.String(8), nullable=True),
        sa.Column("cardinality", sa.String(16), nullable=True),
        sa.Column("provenance_ref", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "retired_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            r"dd_id ~ '^DD\d{3}$'",
            name="ck_dd_id_format",
        ),
        sa.CheckConstraint(
            "entry_kind IN ('canonical','synonym','relationship')",
            name="ck_dd_entry_kind",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_dd_confidence",
        ),
        sa.CheckConstraint(
            "entry_kind <> 'canonical' OR (name IS NOT NULL AND description IS NOT NULL)",
            name="ck_dd_canonical_has_name",
        ),
        sa.CheckConstraint(
            "entry_kind <> 'synonym' OR (surface_term IS NOT NULL AND resolves_to IS NOT NULL)",
            name="ck_dd_synonym_has_target",
        ),
        sa.CheckConstraint(
            "entry_kind <> 'relationship' OR (from_ref IS NOT NULL AND to_ref IS NOT NULL AND cardinality IS NOT NULL)",
            name="ck_dd_relationship_has_ends",
        ),
        sa.ForeignKeyConstraint(
            ["resolves_to"],
            ["data_dictionary_entry.dd_id"],
            name="dd_resolves_to_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["from_ref"],
            ["data_dictionary_entry.dd_id"],
            name="dd_from_ref_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["to_ref"],
            ["data_dictionary_entry.dd_id"],
            name="dd_to_ref_fkey",
        ),
        sa.PrimaryKeyConstraint("dd_id"),
    )

    op.create_table(
        "data_dictionary_resolution_log",
        sa.Column("log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("surface_term", sa.Text(), nullable=False),
        sa.Column("provenance_ref", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "competing_refs",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("auto_recorded", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('existing','synonym','canonical','flagged')",
            name="ck_dd_log_outcome",
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )


def downgrade() -> None:
    op.drop_table("data_dictionary_resolution_log")
    op.drop_table("data_dictionary_entry")

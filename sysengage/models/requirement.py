"""
Requirement ORM model — full Pass 3d implementation.

Per Requirement Derivation Mechanism Spec v0.33 §5.1 and canonical ledger v2.13:
  requirement_id format: R### (R001–R999); composite PK (requirement_id, project_id).
  retired_at IS NULL = active; non-null = retired (FullRerun soft-delete).
  cci_refs / domain_refs / answer_refs / refines_refs are JSONB arrays.
  domain_refs is DM-derived in Stage 4 — never AI-proposed (MD-2).
  refines_refs is populated by the Requirement Matching service (F82/F85);
  Pass 3d always writes [] (§4.4.3).
  requirement_type: three-value triad Functional/Constraint/Structural (F89/v2.13).
  verification_method: gains Measurement (v2.13).
  No direct domain_id FK column: Domain membership is via domain_refs JSONB.

F105 (v0.33): class_model JSONB column — structured class model for Structural
  requirements; NULL for Functional and Constraint types.
  CHECK: class_model IS NULL OR requirement_type = 'Structural'

F107 (v0.33): object_refs JSONB NOT NULL column — materialised object-reference
  paths for behavioural (Functional/Constraint) requirements; always '[]' for
  Structural types.
  CHECK: requirement_type IN ('Functional','Constraint') OR jsonb_array_length(object_refs) = 0
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class RequirementModel(Base):
    __tablename__ = "requirement"
    __table_args__ = (
        CheckConstraint(
            r"requirement_id ~ '^R\d{3}$'",
            name="ck_requirement_id_format",
        ),
        CheckConstraint(
            "length(statement) > 0",
            name="ck_requirement_statement_nonempty",
        ),
        CheckConstraint(
            "requirement_type IN ('Functional','Constraint','Structural')",
            name="ck_requirement_type",
        ),
        CheckConstraint(
            "row_target IN ('1','2','3','4','5','6')",
            name="ck_requirement_row_target",
        ),
        CheckConstraint(
            "jsonb_array_length(cci_refs) >= 1 OR jsonb_array_length(refines_refs) >= 1",
            name="ck_requirement_cci_refs_nonempty",
        ),
        CheckConstraint(
            "jsonb_array_length(domain_refs) >= 1",
            name="ck_requirement_domain_refs_nonempty",
        ),
        CheckConstraint(
            "fit_criteria IS NULL OR length(fit_criteria) > 0",
            name="ck_requirement_fit_criteria",
        ),
        CheckConstraint(
            "verification_method IS NULL OR verification_method IN "
            "('Test','Analysis','Inspection','Demonstration','Measurement')",
            name="ck_requirement_verification_method",
        ),
        CheckConstraint(
            "priority IS NULL OR priority IN ('High','Medium','Low')",
            name="ck_requirement_priority",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_requirement_confidence",
        ),
        CheckConstraint(
            "class_model IS NULL OR requirement_type = 'Structural'",
            name="ck_requirement_class_model_structural_only",
        ),
        CheckConstraint(
            "requirement_type IN ('Functional','Constraint') OR jsonb_array_length(object_refs) = 0",
            name="ck_requirement_object_refs_behavioural_only",
        ),
        ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="requirement_project_id_fkey",
        ),
    )

    requirement_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    row_target: Mapped[str] = mapped_column(String(1), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    cci_refs: Mapped[list] = mapped_column(JSONB, nullable=False)
    domain_refs: Mapped[list] = mapped_column(JSONB, nullable=False)
    fit_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(8), nullable=True)
    answer_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb"
    )
    refines_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb"
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    class_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    object_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    project = relationship("ProjectModel", back_populates="requirements")

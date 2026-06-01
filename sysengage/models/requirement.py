"""
Requirement ORM model — full Pass 3d implementation.

Per Requirement Derivation Mechanism Spec v0.1 §5.1 and canonical ledger v2.12:
  requirement_id format: R### (R001–R999); composite PK (requirement_id, project_id).
  retired_at IS NULL = active; non-null = retired (FullRerun soft-delete).
  cci_refs / domain_refs / answer_refs are JSONB arrays stored directly on the row.
  domain_refs is DM-derived in Stage 4 — never AI-proposed (MD-2).
  No direct domain_id FK column: Domain membership is via domain_refs JSONB.
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
            "requirement_type IN ('Functional','Constraint','Performance','Suitability','Non-Functional')",
            name="ck_requirement_type",
        ),
        CheckConstraint(
            "row_target IN ('1','2','3','4','5','6')",
            name="ck_requirement_row_target",
        ),
        CheckConstraint(
            "jsonb_array_length(cci_refs) >= 1",
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
            "verification_method IS NULL OR verification_method IN ('Test','Analysis','Inspection','Demonstration')",
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
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="requirements")

"""
Concern ORM model — persistence for canonical Concern entities.

Per canonical ledger spec v2.12 Concern element type.
concern_id format: CN### (from cn_id_seq Postgres sequence). No hyphen.

source_refs is a JSONB array (list of ID strings: Source IDs, SourceAtom IDs,
or Requirement IDs) per canonical spec.

Non-canonical attributes (implementation-internal, stripped at export):
  project_id — multi-tenancy FK anchor.
  created_at — implementation timestamp.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class ConcernModel(Base):
    __tablename__ = "concern"
    __table_args__ = (
        CheckConstraint(r"concern_id ~ '^CN\d{3,}$'", name="ck_concern_id_format"),
    )

    concern_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="Open")
    produced_in_row: Mapped[str] = mapped_column(String, nullable=False)
    practitioner_id: Mapped[str] = mapped_column(
        String, ForeignKey("stakeholder.stakeholder_id"), nullable=False
    )
    dispositioned_with_outcome: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    disposition_rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="concerns")
    practitioner = relationship("StakeholderModel", back_populates="concerns")

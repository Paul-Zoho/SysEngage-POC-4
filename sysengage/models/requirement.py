"""
Requirement ORM model — minimal stub for Phase 3 Pass 3a reading.

Phase 3 Passes 3b-3d produce Requirement entities. This stub provides
the columns needed for Stage 1 (chunk assembly) reading:
  requirement_id, statement (text), row_target, domain_id, project_id.

Extended in Phase 3 Passes 3b-3d implementation.
requirement_id format: R### per canonical ledger spec v2.12.

domain_id — FK to domain (single domain per requirement for stub;
v2.12 domain_refs list relationship extended by Phase 3b-3d).
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class RequirementModel(Base):
    __tablename__ = "requirement"

    requirement_id: Mapped[str] = mapped_column(String, primary_key=True)
    statement: Mapped[str] = mapped_column(String, nullable=False)
    row_target: Mapped[str] = mapped_column(String, nullable=False)
    domain_id: Mapped[str] = mapped_column(
        String, ForeignKey("domain.domain_id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    domain = relationship("DomainModel", back_populates="requirements")
    project = relationship("ProjectModel", back_populates="requirements")

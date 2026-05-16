"""
Domain ORM model — minimal stub for Phase 3 Pass 3a reading.

Phase 3 Passes 3b-3d produce Domain entities. This stub provides
just the columns needed for Stage 1 (chunk assembly) reading:
  domain_id, name, row_target, project_id.

Extended in Phase 3 Passes 3b-3d implementation.
domain_id format: D### per canonical ledger spec v2.12.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class DomainModel(Base):
    __tablename__ = "domain"

    domain_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    row_target: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="domains")
    requirements = relationship("RequirementModel", back_populates="domain")

"""
Requirement ORM model — stub updated for Pass 3c composite domain PK.

domain table now has composite PK (domain_id, project_id); this stub
carries the same composite FK so referential integrity is maintained.
requirement_id format: R### per canonical ledger spec v2.12.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class RequirementModel(Base):
    __tablename__ = "requirement"
    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "project_id"],
            ["domain.domain_id", "domain.project_id"],
            name="requirement_domain_composite_fk",
        ),
        ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="requirement_project_id_fkey",
        ),
    )

    requirement_id: Mapped[str] = mapped_column(String, primary_key=True)
    statement: Mapped[str] = mapped_column(String, nullable=False)
    row_target: Mapped[str] = mapped_column(String, nullable=False)
    domain_id: Mapped[str] = mapped_column(String(10), nullable=False)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    domain = relationship(
        "DomainModel",
        back_populates="requirements",
        foreign_keys="[RequirementModel.domain_id, RequirementModel.project_id]",
        overlaps="project,requirements",
    )
    project = relationship(
        "ProjectModel",
        back_populates="requirements",
        overlaps="domain,requirements",
    )

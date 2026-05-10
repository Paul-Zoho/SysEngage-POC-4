"""
Project ORM model — minimal for v1 single-tenant prototype.

Provides the project_id FK anchor required by Source, Segment, SourceAtom,
and AnalysisPass. Not a canonical ledger entity; infrastructure only.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class ProjectModel(Base):
    __tablename__ = "project"

    project_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    segments = relationship("SegmentModel", back_populates="project")
    sources = relationship("SourceModel", back_populates="project")
    source_atoms = relationship("SourceAtomModel", back_populates="project")
    analysis_passes = relationship("AnalysisPassModel", back_populates="project")

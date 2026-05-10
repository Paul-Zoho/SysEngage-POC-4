"""
Source ORM model — persistence for canonical Source entity.

Per Implementation Spec §5.2: source table with FK to segment (nullable).
Sequence s_id_seq generates the numeric part of S### identifiers.

Implementation note: segment_id FK is the DB-level representation of the
context_id relationship (Pass 0B assigns each Source to its parent Segment).
The canonical Segment.source_refs list is derived from this FK at query time.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class SourceModel(Base):
    __tablename__ = "source"

    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    segmentation_context: Mapped[str] = mapped_column(String, nullable=False)
    parent_source_ref: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    input_material_ref: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    segment_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("segment.segment_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_non_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_decoding_issues: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="sources")
    segment = relationship("SegmentModel", back_populates="sources")
    parent_source = relationship("SourceModel", remote_side="SourceModel.source_id")
    source_atoms = relationship(
        "SourceAtomModel", back_populates="source", cascade="all, delete-orphan"
    )

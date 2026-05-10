"""
Segment ORM model — persistence for canonical Segment entity.

Per Implementation Spec §5.2: segment table with FK to project.
Sequence seg_id_seq generates the numeric part of SEG### identifiers.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class SegmentModel(Base):
    __tablename__ = "segment"

    segment_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_segment_ref: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("segment.segment_id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="segments")
    sources = relationship("SourceModel", back_populates="segment")
    parent_segment = relationship("SegmentModel", remote_side="SegmentModel.segment_id")

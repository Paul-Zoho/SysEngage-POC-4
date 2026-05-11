"""
Segment ORM model — persistence for canonical Segment entity.

Per Implementation Spec v0.4 §5.2 and canonical ledger spec v2.11.
Sequence seg_id_seq generates the numeric part of SEG### identifiers.

source_refs stored as PostgreSQL ARRAY(String) — each entry is a source_id
referencing a canonical Source entity. This is the canonical Segment → Source
relation per v2.11: Segment groups Sources by listing their IDs. Sources do
NOT back-reference Segment (no segment_id FK on Source per F24 fix).

Non-canonical attributes (stripped at export per F24): project_id, created_at.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class SegmentModel(Base):
    __tablename__ = "segment"

    segment_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_refs: Mapped[list] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
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
    parent_segment = relationship("SegmentModel", remote_side="SegmentModel.segment_id")

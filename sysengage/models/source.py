"""
Source ORM model — persistence for canonical Source entity.

Per Implementation Spec v0.4 §5.2 and canonical ledger spec v2.11.
Sequence s_id_seq generates the numeric part of S### identifiers.

NO segment_id column on Source (F24 fix). The canonical Segment → Source
relation is expressed via Segment.source_refs (ARRAY of source_id values).
Source has no back-reference FK to Segment — removing segment_id eliminates
the inverted non-canonical relation that contradicted v2.11.

Non-canonical attributes (implementation-internal, stripped at export per F24):
is_non_text, has_decoding_issues, project_id, created_at.
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
    parent_source = relationship("SourceModel", remote_side="SourceModel.source_id")
    source_atoms = relationship(
        "SourceAtomModel", back_populates="source", cascade="all, delete-orphan"
    )

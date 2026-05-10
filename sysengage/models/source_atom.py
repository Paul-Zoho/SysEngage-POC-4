"""
SourceAtom ORM model — persistence for canonical SourceAtom entity.

Per Implementation Spec §5.2: source_atom table with FK to source (NOT NULL, CASCADE).
Sequence sa_id_seq generates the numeric part of SA### identifiers.

Implementation extension: position column (int) is not in canonical spec v2.9
but is required by Implementation Spec §4.4.3 for atom ordering within parent Source.
Finding F21 documented in schemas/source_atom.py.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class SourceAtomModel(Base):
    __tablename__ = "source_atom"

    atom_id: Mapped[str] = mapped_column(String, primary_key=True)
    atom_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(
        String,
        ForeignKey("source.source_id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_ref: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("segment.segment_id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_atom_ref: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("source_atom.atom_id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    source = relationship("SourceModel", back_populates="source_atoms")
    segment = relationship("SegmentModel")
    parent_atom = relationship(
        "SourceAtomModel", remote_side="SourceAtomModel.atom_id"
    )
    project = relationship("ProjectModel", back_populates="source_atoms")

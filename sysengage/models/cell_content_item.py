"""
CellContentItem ORM model.

Per CCI Construction Mechanism Spec v0.2 §5.2 and canonical ledger spec v2.12:
  ci_id format: CCI-ROW{row}-C-{column}-{seq}  e.g. CCI-ROW2-C-What-001
  Sequence is three-digit zero-padded, scoped per ZachmanCell.
  ci_id is immutable once assigned — on re-run, signal_refs, confidence, and
  description may be updated in-place; ci_id never changes.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class CellContentItemModel(Base):
    __tablename__ = "cell_content_item"
    __table_args__ = (
        CheckConstraint(
            r"ci_id ~ '^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$'",
            name="ck_cci_id_format",
        ),
    )

    ci_id: Mapped[str] = mapped_column(String, primary_key=True)
    cell_id: Mapped[str] = mapped_column(
        String, ForeignKey("zachman_cell.cell_id", ondelete="CASCADE"), nullable=False
    )
    classification_type: Mapped[str] = mapped_column(String, nullable=False)
    signal_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False, primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    zachman_cell = relationship("ZachmanCellModel", back_populates="cell_content_items")

"""
Signal ORM model — persistence for canonical Signal entities.

Per canonical ledger spec v2.12 Signal element type.
signal_id format: SG### (from sg_id_seq Postgres sequence).

source_refs and sourceatom_refs are JSONB arrays (list of ID strings).
This matches the canonical spec's list[str] attribute type and avoids
a separate join table for what is typically a small per-entity list.

Non-canonical attributes (implementation-internal, stripped at export):
  project_id — multi-tenancy FK anchor for scoped queries.
  created_at — implementation timestamp.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class SignalModel(Base):
    __tablename__ = "signal"
    __table_args__ = (
        CheckConstraint(r"signal_id ~ '^SG\d{3,}$'", name="ck_signal_id_format"),
    )

    signal_id: Mapped[str] = mapped_column(String, primary_key=True)
    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    row_target: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sourceatom_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    derived_from_concern_id: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="signals")

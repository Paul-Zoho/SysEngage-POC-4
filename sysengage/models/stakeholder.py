"""
Stakeholder ORM model — minimal for v1.

SH001 is the reserved SysEngage Tool Stakeholder per canonical ledger spec v2.9.
Practitioners are additional stakeholder records.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class StakeholderModel(Base):
    __tablename__ = "stakeholder"

    stakeholder_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stakeholder_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    analysis_passes = relationship("AnalysisPassModel", back_populates="practitioner")

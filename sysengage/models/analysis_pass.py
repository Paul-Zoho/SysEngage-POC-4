"""
AnalysisPass ORM model — persistence for audit trail entity.

Per Implementation Spec §5.2 and Row 4 Applied §10.
JSONB outputs column holds: read_witness, mechanism_data, mode_violations,
failure_reason, failure_pass (per F4/F10 architectural commitments).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class AnalysisPassModel(Base):
    __tablename__ = "analysis_pass"

    pass_id: Mapped[str] = mapped_column(String, primary_key=True)
    phase_id: Mapped[str] = mapped_column(String, nullable=False, default="PH001")
    pass_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    pass_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_status: Mapped[str] = mapped_column(String, nullable=False)
    mode_active: Mapped[str] = mapped_column(String, nullable=False, default="LPM")
    declared_transformation_modes: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practitioner_id: Mapped[str] = mapped_column(
        String, ForeignKey("stakeholder.stakeholder_id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    outputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    practitioner = relationship("StakeholderModel", back_populates="analysis_passes")
    project = relationship("ProjectModel", back_populates="analysis_passes")

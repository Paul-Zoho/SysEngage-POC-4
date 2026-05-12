"""
AnalysisPass ORM model — persistence for audit trail entity.

Per Implementation Spec v0.4 §5.2, Row 4 Applied §10, and canonical ledger spec v2.11.
JSONB outputs column holds: read_witness, mechanism_data, mode_violations,
failure_reason, failure_pass (per F4/F10 architectural commitments).

Canonical attributes per v2.11 (F25/F27 resolution — 4 columns previously missing):
  pass_type, mechanism, evaluated_scope, confidence added as dedicated columns
  so they can be queried independently and included in canonical export (F25).

Non-canonical attributes (kept for operational use, stripped at export per F24):
  phase_id — intentional placeholder for multi-Phase tracking (Q7: Possibility 3;
  v0.4 §7.2 references it; keep in DB, strip at export).
  practitioner_id, project_id — multi-tenancy FK anchors.
  created_at — implementation-internal timestamp.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class AnalysisPassModel(Base):
    __tablename__ = "analysis_pass"

    pass_id: Mapped[str] = mapped_column(String, primary_key=True)
    phase_id: Mapped[str] = mapped_column(String, nullable=False, default="PH001")
    pass_type: Mapped[str] = mapped_column(String, nullable=False, default="Universal")
    mechanism: Mapped[str] = mapped_column(String, nullable=False, default="SourceCapture")
    evaluated_scope: Mapped[str] = mapped_column(
        String, nullable=False, default="All input material in this project"
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    pass_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    pass_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_status: Mapped[str] = mapped_column(String, nullable=False)
    mode_active: Mapped[str] = mapped_column(String, nullable=False, default="LPM")
    declared_transformation_modes: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practitioner_id: Mapped[str] = mapped_column(
        String, ForeignKey("stakeholder.stakeholder_id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False
    )
    outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    practitioner = relationship("StakeholderModel", back_populates="analysis_passes")
    project = relationship("ProjectModel", back_populates="analysis_passes")

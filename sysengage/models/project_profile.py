"""
ProjectProfile ORM model — per-project configuration for AI-involving mechanisms.

One-to-one with project (project_id is PK and FK to project).
Holds mechanism configuration thresholds that drive Phase 3 behaviour.

Per Row-Lens Source Re-Analysis spec v0.1 §3.2 and §4.1/§4.2:
  concern_threshold — T1 for Signal/Concern classification (default 0.65).
  chunk_match_threshold — fuzzy match threshold for Stage 1 (default 0.6).
  residual_batch_size — batch size for residual AI invocations (default 50).

Per CCI Construction Mechanism Spec v0.8 §3.2 and §3.3:
  cci_consolidation_threshold — over-consolidation flag threshold (default 0.80).
  cci_batch_size — signals per AI batch invocation in Step 3 (default 20).
  stage4a_similarity_threshold — Jaccard description similarity required for
    Stage 4a auto-merge (default 0.60). Pairs with matching type + refs but
    similarity below threshold are routed to Stage 4b instead.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class ProjectProfileModel(Base):
    __tablename__ = "project_profile"

    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), primary_key=True
    )
    concern_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.65
    )
    chunk_match_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.6
    )
    residual_batch_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50
    )
    cci_consolidation_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.80
    )
    cci_batch_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    stage4a_similarity_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.60
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="project_profile")

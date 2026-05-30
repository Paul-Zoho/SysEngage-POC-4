"""
Domain ORM model — full Pass 3c implementation.

Per Domain Derivation Mechanism Spec v0.14 §5.1 and canonical ledger spec v2.12:
  domain_id format: D### (D001–D999); composite PK (domain_id, project_id).
  retired_at IS NULL = active; non-null = retired (FullRerun soft-delete).
  domain_qualifier and upstream_domain_ref are WITHDRAWN — neither column here.
  Six canonical attributes: domain_id, name, description, classification_type,
    row_target, cell_content_item_refs (JSONB array directly on domain row —
    no join table; see MD-4 in spec v0.14).
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class DomainModel(Base):
    __tablename__ = "domain"
    __table_args__ = (
        CheckConstraint(
            r"domain_id ~ '^D\d{3}$'",
            name="ck_domain_id_format",
        ),
        CheckConstraint(
            "row_target IN ('1','2','3','4','5','6')",
            name="ck_domain_row_target",
        ),
        ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name="domain_project_id_fkey",
        ),
    )

    domain_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    classification_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_target: Mapped[str] = mapped_column(String(1), nullable=False)
    cell_content_item_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb"
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project = relationship("ProjectModel", back_populates="domains")
    requirements = relationship(
        "RequirementModel",
        back_populates="domain",
        overlaps="project,requirements",
    )

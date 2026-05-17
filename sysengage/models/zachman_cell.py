"""
ZachmanCell ORM model.

Per CCI Construction Mechanism Spec v0.2 §5.1 and canonical ledger spec v2.12:
  cell_id format: ZC-R{row}-C-{column}  e.g. ZC-R2-C-What
  Six cells per row — upserted idempotently on every Pass 3b run.
  One-to-many relationship to CellContentItemModel.

PK is composite (cell_id, project_id) — cell_id is NOT globally unique across
projects.  Two projects can each have ZC-R1-C-What; composite PK enforces
per-project uniqueness (mirror of cell_content_item composite PK).
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ZachmanCellModel(Base):
    __tablename__ = "zachman_cell"
    __table_args__ = (
        CheckConstraint(
            r"cell_id ~ '^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$'",
            name="ck_zachman_cell_id_format",
        ),
        CheckConstraint(
            '"column" IN (\'What\',\'How\',\'Where\',\'Who\',\'When\',\'Why\')',
            name="ck_zachman_cell_column",
        ),
    )

    cell_id: Mapped[str] = mapped_column(String, primary_key=True)
    row_target: Mapped[str] = mapped_column(String, nullable=False)
    column: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("project.project_id"), nullable=False, primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    cell_content_items = relationship(
        "CellContentItemModel", back_populates="zachman_cell"
    )

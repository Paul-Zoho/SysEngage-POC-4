"""
DomainCCIMembership ORM model — join table for Domain ↔ CCI membership.

Per Domain Derivation Mechanism Spec v0.13 §5.1:
  Implements cell_content_item_refs as a join table rather than a JSONB array.
  Enables efficient bidirectional queries and enforces FK integrity.
  Composite PK: (domain_id, project_id, ci_id).

FKs:
  (domain_id, project_id) → domain(domain_id, project_id)
  (ci_id, project_id)     → cell_content_item(ci_id, project_id)
"""

from sqlalchemy import ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class DomainCCIMembershipModel(Base):
    __tablename__ = "domain_cci_membership"
    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "project_id"],
            ["domain.domain_id", "domain.project_id"],
            name="dcm_domain_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["ci_id", "project_id"],
            ["cell_content_item.ci_id", "cell_content_item.project_id"],
            name="dcm_cci_fkey",
        ),
    )

    domain_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    ci_id: Mapped[str] = mapped_column(String(60), primary_key=True)

    domain = relationship(
        "DomainModel",
        back_populates="memberships",
        foreign_keys="[DomainCCIMembershipModel.domain_id, DomainCCIMembershipModel.project_id]",
    )

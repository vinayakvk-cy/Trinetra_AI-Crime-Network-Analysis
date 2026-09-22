from __future__ import annotations

from enum import Enum

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# CASE ENTITY RELATION TYPE
# ============================================================


class CaseEntityRelation(str, Enum):
    """
    Describes how an entity is related to a case.
    """

    SUSPECT = "suspect"

    VICTIM = "victim"

    WITNESS = "witness"

    PERSON_OF_INTEREST = "person_of_interest"

    OFFICER = "officer"

    VEHICLE = "vehicle"

    LOCATION = "location"

    ORGANIZATION = "organization"

    PHONE = "phone"

    ACCOUNT = "account"

    EVIDENCE_ENTITY = "evidence_entity"

    RELATED = "related"

    OTHER = "other"


# ============================================================
# CASE ENTITY MODEL
# ============================================================


class CaseEntity(FullBaseModel):
    """
    Association between a case and an entity.

    Example:

        Case #1
            |
            ├── Arun Kumar       → suspect
            ├── KA01AB1234       → vehicle
            └── Bangalore        → location

    This allows the same entity to participate
    in multiple cases.
    """

    __tablename__ = "case_entities"

    # ========================================================
    # CASE REFERENCE
    # ========================================================

    case_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # ENTITY REFERENCE
    # ========================================================

    entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # RELATION
    # ========================================================

    relation: Mapped[CaseEntityRelation] = mapped_column(
        default=CaseEntityRelation.RELATED,
        nullable=False,
        index=True,
    )

    # ========================================================
    # NOTES
    # ========================================================

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # TABLE CONSTRAINTS
    # ========================================================

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "entity_id",
            "relation",
            name="uq_case_entity_relation",
        ),
    )

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<CaseEntity("
            f"id={self.id}, "
            f"case_id={self.case_id}, "
            f"entity_id={self.entity_id}, "
            f"relation='{self.relation.value}'"
            f")>"
        )
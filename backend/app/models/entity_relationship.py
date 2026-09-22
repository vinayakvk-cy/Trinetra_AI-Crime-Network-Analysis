from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# ENTITY RELATIONSHIP TYPE
# ============================================================


class EntityRelationshipType(str, Enum):
    """
    Supported relationships between TRINETRA entities.
    """

    ASSOCIATED_WITH = "associated_with"

    KNOWS = "knows"

    OWNS = "owns"

    USES = "uses"

    CONTACTED = "contacted"

    CALLED = "called"

    VISITED = "visited"

    LOCATED_AT = "located_at"

    TRAVELED_TO = "traveled_to"

    WORKS_FOR = "works_for"

    MEMBER_OF = "member_of"

    CONNECTED_TO = "connected_to"

    TRANSFERRED_TO = "transferred_to"

    RECEIVED_FROM = "received_from"

    REGISTERED_TO = "registered_to"

    BELONGS_TO = "belongs_to"

    LINKED_TO = "linked_to"

    RELATED_TO = "related_to"

    OTHER = "other"


# ============================================================
# ENTITY RELATIONSHIP MODEL
# ============================================================


class EntityRelationship(FullBaseModel):
    """
    Represents a relationship between two entities.

    Example:

        Person
            |
            | owns
            v
        Vehicle

    A relationship can optionally be supported
    by a piece of evidence.
    """

    __tablename__ = "entity_relationships"

    # ========================================================
    # SOURCE ENTITY
    # ========================================================

    source_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # TARGET ENTITY
    # ========================================================

    target_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # RELATIONSHIP TYPE
    # ========================================================

    relationship_type: Mapped[EntityRelationshipType] = mapped_column(
        nullable=False,
        index=True,
    )

    # ========================================================
    # DESCRIPTION
    # ========================================================

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # RELATIONSHIP CONFIDENCE
    # ========================================================

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # SOURCE INFORMATION
    # ========================================================

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ========================================================
    # EVIDENCE REFERENCE
    # ========================================================

    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "evidence.id",
            ondelete="SET NULL",
        ),
        nullable=True,
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
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_entity_relationship",
        ),
    )

    # ========================================================
    # RELATIONSHIP METHODS
    # ========================================================

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set relationship confidence.

        Expected range:

            0.0 → 1.0
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Relationship confidence must be between 0.0 and 1.0."
            )

        self.confidence = confidence

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<EntityRelationship("
            f"id={self.id}, "
            f"source_entity_id={self.source_entity_id}, "
            f"target_entity_id={self.target_entity_id}, "
            f"relationship_type='{self.relationship_type.value}', "
            f"confidence={self.confidence}, "
            f"evidence_id={self.evidence_id}"
            f")>"
        )
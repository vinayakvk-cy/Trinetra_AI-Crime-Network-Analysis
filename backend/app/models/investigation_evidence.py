from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# INVESTIGATION EVIDENCE RELATION TYPE
# ============================================================

class InvestigationEvidenceRelation(str, Enum):
    """
    Describes how a piece of evidence is related to an
    investigation.
    """

    RELEVANT = "relevant"

    PRIMARY = "primary"

    SUPPORTING = "supporting"

    RELATED = "related"

    REVIEWED = "reviewed"

    DISPUTED = "disputed"


# ============================================================
# INVESTIGATION EVIDENCE MODEL
# ============================================================

class InvestigationEvidence(FullBaseModel):
    """
    Association between an investigation and a piece of evidence.

    This creates the database connection:

        Investigation
              |
              |
        InvestigationEvidence
              |
              |
           Evidence

    This is a many-to-many association model:

        One investigation -> many evidence records
        One evidence -> many investigations

    Example:

        Investigation #1
            ├── Evidence #1
            ├── Evidence #2
            └── Evidence #3

        Investigation #2
            ├── Evidence #2
            └── Evidence #4
    """

    __tablename__ = "investigation_evidence"

    # ========================================================
    # INVESTIGATION REFERENCE
    # ========================================================

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "investigations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # EVIDENCE REFERENCE
    # ========================================================

    evidence_id: Mapped[int] = mapped_column(
        ForeignKey(
            "evidence.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # RELATIONSHIP TYPE
    # ========================================================

    relation: Mapped[InvestigationEvidenceRelation] = mapped_column(
        default=InvestigationEvidenceRelation.RELEVANT,
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
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<InvestigationEvidence("
            f"id={self.id}, "
            f"investigation_id={self.investigation_id}, "
            f"evidence_id={self.evidence_id}, "
            f"relation='{self.relation.value}'"
            f")>"
        )
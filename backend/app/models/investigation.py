"""
TRINETRA Investigation Database Model
======================================

Represents an investigation performed against a case.

An investigation may contain:

    - Investigator information
    - Investigation status
    - Investigation objectives
    - Analytical findings
    - Suspect/lead review
    - Investigator actions
    - Final findings
    - Resolution information

Individual investigator tasks/actions are managed by:

    app/investigations/action_manager.py

Reusable investigation patterns/memory are managed by:

    app/investigations/case_memory.py

Graph relationships are handled separately by Neo4j.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# INVESTIGATION STATUS
# ============================================================


class InvestigationStatus(str, Enum):
    """
    Current state of an investigation.
    """

    CREATED = "created"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    EVIDENCE_REVIEW = "evidence_review"
    SUSPECT_VERIFICATION = "suspect_verification"
    CROSS_CASE_ANALYSIS = "cross_case_analysis"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# ============================================================
# INVESTIGATION OUTCOME
# ============================================================


class InvestigationOutcome(str, Enum):
    """
    Final outcome of an investigation.

    These values represent the investigation's analytical
    conclusion, not a legal determination.
    """

    UNDETERMINED = "undetermined"
    LEAD_SUPPORTED = "lead_supported"
    LEAD_NOT_SUPPORTED = "lead_not_supported"
    INCONCLUSIVE = "inconclusive"
    CASE_SOLVED = "case_solved"
    REFERRED = "referred"


# ============================================================
# INVESTIGATION MODEL
# ============================================================


class Investigation(FullBaseModel):
    """
    Investigation record associated with a TRINETRA case.

    One case can have multiple investigations over its
    lifetime.
    """

    __tablename__ = "investigations"

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
    # INVESTIGATION IDENTIFICATION
    # ========================================================

    investigation_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    objective: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # STATUS
    # ========================================================

    # Store enum VALUES in the database:
    #
    # created
    # planning
    # in_progress
    # evidence_review
    # etc.
    #
    # This keeps the database/API representation consistent.

    status: Mapped[InvestigationStatus] = mapped_column(
        SQLEnum(
            InvestigationStatus,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        default=InvestigationStatus.CREATED,
        nullable=False,
        index=True,
    )

    outcome: Mapped[InvestigationOutcome] = mapped_column(
        SQLEnum(
            InvestigationOutcome,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        default=InvestigationOutcome.UNDETERMINED,
        nullable=False,
    )

    # ========================================================
    # INVESTIGATOR
    # ========================================================

    investigator: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    investigation_unit: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # INVESTIGATION FINDINGS
    # ========================================================

    findings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    conclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # ANALYTICAL RESULTS
    # ========================================================

    initial_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    final_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    initial_suspect_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    final_suspect_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # GRAPH REFERENCE
    # ========================================================

    graph_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ========================================================
    # INVESTIGATION TIMELINE
    # ========================================================

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ========================================================
    # STATUS METHODS
    # ========================================================

    def start(self) -> None:
        """
        Start the investigation.
        """

        self.status = InvestigationStatus.IN_PROGRESS

        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

    def begin_planning(self) -> None:
        """
        Put the investigation into planning.
        """

        self.status = InvestigationStatus.PLANNING

    def begin_evidence_review(self) -> None:
        """
        Start evidence review.
        """

        self.status = InvestigationStatus.EVIDENCE_REVIEW

    def begin_suspect_verification(self) -> None:
        """
        Begin verification of an analytical lead.

        This does not establish guilt. It only records that
        the investigation has entered a verification stage.
        """

        self.status = InvestigationStatus.SUSPECT_VERIFICATION

    def begin_cross_case_analysis(self) -> None:
        """
        Start cross-case analysis.
        """

        self.status = InvestigationStatus.CROSS_CASE_ANALYSIS

    def suspend(self) -> None:
        """
        Temporarily suspend the investigation.
        """

        self.status = InvestigationStatus.SUSPENDED

    def complete(
        self,
        outcome: InvestigationOutcome,
        conclusion: str | None = None,
    ) -> None:
        """
        Complete the investigation.

        Parameters
        ----------
        outcome:
            Final investigation outcome.

        conclusion:
            Optional final conclusion.
        """

        self.status = InvestigationStatus.COMPLETED
        self.outcome = outcome

        if conclusion is not None:
            self.conclusion = conclusion

        self.completed_at = datetime.now(timezone.utc)

    def close(self) -> None:
        """
        Close the investigation.
        """

        self.status = InvestigationStatus.CLOSED

        if self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)

    # ========================================================
    # ANALYTICAL SCORE METHODS
    # ========================================================

    def set_initial_risk_score(
        self,
        score: float,
    ) -> None:
        """
        Store the initial analytical risk score.

        Expected range:
            0.0 -> 100.0
        """

        if not 0.0 <= score <= 100.0:
            raise ValueError(
                "Risk score must be between 0 and 100."
            )

        self.initial_risk_score = score

    def set_final_risk_score(
        self,
        score: float,
    ) -> None:
        """
        Store the final analytical risk score.

        Expected range:
            0.0 -> 100.0
        """

        if not 0.0 <= score <= 100.0:
            raise ValueError(
                "Risk score must be between 0 and 100."
            )

        self.final_risk_score = score

    def set_initial_suspect_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Store the initial analytical suspect confidence.

        Expected range:
            0.0 -> 100.0
        """

        if not 0.0 <= confidence <= 100.0:
            raise ValueError(
                "Suspect confidence must be between 0 and 100."
            )

        self.initial_suspect_confidence = confidence

    def set_final_suspect_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Store the final analytical suspect confidence.

        Expected range:
            0.0 -> 100.0
        """

        if not 0.0 <= confidence <= 100.0:
            raise ValueError(
                "Suspect confidence must be between 0 and 100."
            )

        self.final_suspect_confidence = confidence

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<Investigation("
            f"id={self.id}, "
            f"investigation_number="
            f"'{self.investigation_number}', "
            f"status='{self.status.value}', "
            f"outcome='{self.outcome.value}'"
            f")>"
        )
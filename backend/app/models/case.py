from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ============================================================
# CASE STATUS
# ============================================================

class CaseStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


# ============================================================
# CASE PRIORITY
# ============================================================

class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# CASE MODEL
# ============================================================

class Case(Base):
    """
    Investigation case database model.
    """

    __tablename__ = "cases"

    # --------------------------------------------------------
    # PRIMARY KEY
    # --------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # --------------------------------------------------------
    # BASIC CASE INFORMATION
    # --------------------------------------------------------

    case_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # CASE STATUS / PRIORITY
    # --------------------------------------------------------

    status: Mapped[CaseStatus] = mapped_column(
        nullable=False,
        default=CaseStatus.NEW,
    )

    priority: Mapped[CasePriority] = mapped_column(
        nullable=False,
        default=CasePriority.MEDIUM,
    )

    # --------------------------------------------------------
    # FIR INFORMATION
    # --------------------------------------------------------

    fir_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    fir_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    police_station: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    jurisdiction: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # --------------------------------------------------------
    # INCIDENT INFORMATION
    # --------------------------------------------------------

    incident_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    incident_location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    crime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # INVESTIGATION INFORMATION
    # --------------------------------------------------------

    investigating_officer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    investigating_unit: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # --------------------------------------------------------
    # AI / RISK INFORMATION
    # --------------------------------------------------------

    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    suspect_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    graph_node_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # CASE LIFECYCLE
    # --------------------------------------------------------

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # --------------------------------------------------------
    # AUDIT TIMESTAMPS
    # --------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # --------------------------------------------------------
    # AUDIT USERS
    # --------------------------------------------------------

    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # --------------------------------------------------------
    # REPRESENTATION
    # --------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Case("
            f"id={self.id}, "
            f"case_number={self.case_number!r}, "
            f"title={self.title!r}, "
            f"status={self.status.value!r}"
            f")>"
        )
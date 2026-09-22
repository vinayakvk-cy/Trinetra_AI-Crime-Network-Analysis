from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# ENUMS
# ============================================================

class CaseStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# CASE BASE
# ============================================================

class CaseBase(BaseModel):
    case_number: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)

    description: str | None = None

    status: CaseStatus = CaseStatus.NEW
    priority: CasePriority = CasePriority.MEDIUM

    fir_number: str | None = None
    fir_date: datetime | None = None

    police_station: str | None = None
    jurisdiction: str | None = None

    incident_date: datetime | None = None
    incident_location: str | None = None
    crime_type: str | None = None

    investigating_officer: str | None = None
    investigating_unit: str | None = None

    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    suspect_confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    graph_node_id: str | None = None

    opened_at: datetime | None = None
    closed_at: datetime | None = None


# ============================================================
# CREATE CASE
# ============================================================

class CaseCreate(CaseBase):
    """
    Schema used when creating a case.
    """

    pass


# ============================================================
# UPDATE CASE
# ============================================================

class CaseUpdate(BaseModel):
    """
    All fields are optional for PATCH requests.
    """

    case_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    status: CaseStatus | None = None
    priority: CasePriority | None = None

    fir_number: str | None = None
    fir_date: datetime | None = None

    police_station: str | None = None
    jurisdiction: str | None = None

    incident_date: datetime | None = None
    incident_location: str | None = None
    crime_type: str | None = None

    investigating_officer: str | None = None
    investigating_unit: str | None = None

    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    suspect_confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    graph_node_id: str | None = None

    opened_at: datetime | None = None
    closed_at: datetime | None = None

    created_by: str | None = None
    updated_by: str | None = None


# ============================================================
# CASE RESPONSE
# ============================================================

class CaseResponse(BaseModel):
    """
    Schema returned by the API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int

    case_number: str
    title: str
    description: str | None = None

    status: CaseStatus
    priority: CasePriority

    fir_number: str | None = None
    fir_date: datetime | None = None

    police_station: str | None = None
    jurisdiction: str | None = None

    incident_date: datetime | None = None
    incident_location: str | None = None
    crime_type: str | None = None

    investigating_officer: str | None = None
    investigating_unit: str | None = None

    risk_score: float | None = None
    suspect_confidence: float | None = None

    graph_node_id: str | None = None

    opened_at: datetime | None = None
    closed_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    created_by: str | None = None
    updated_by: str | None = None
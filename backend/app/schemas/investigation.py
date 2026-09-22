from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.investigation import (
    InvestigationOutcome,
    InvestigationStatus,
)


# ============================================================
# INVESTIGATION BASE
# ============================================================


class InvestigationBase(BaseModel):
    """
    Common fields shared by investigation create and response
    schemas.
    """

    case_id: int = Field(
        ...,
        gt=0,
        description="ID of the case this investigation belongs to.",
    )

    investigation_number: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    objective: str | None = None

    status: InvestigationStatus = (
        InvestigationStatus.CREATED
    )

    outcome: InvestigationOutcome = (
        InvestigationOutcome.UNDETERMINED
    )

    investigator: str | None = None

    investigation_unit: str | None = None

    findings: str | None = None

    conclusion: str | None = None

    initial_risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    final_risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    initial_suspect_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    final_suspect_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    graph_reference: str | None = Field(
        default=None,
        max_length=500,
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None


# ============================================================
# CREATE INVESTIGATION
# ============================================================


class InvestigationCreate(InvestigationBase):
    """
    Schema used when creating a new investigation.
    """

    pass


# ============================================================
# UPDATE INVESTIGATION
# ============================================================


class InvestigationUpdate(BaseModel):
    """
    Schema used for partial investigation updates.

    Every field is optional because PATCH requests should
    update only the fields supplied by the client.
    """

    case_id: int | None = Field(
        default=None,
        gt=0,
    )

    investigation_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    objective: str | None = None

    status: InvestigationStatus | None = None

    outcome: InvestigationOutcome | None = None

    investigator: str | None = None

    investigation_unit: str | None = None

    findings: str | None = None

    conclusion: str | None = None

    initial_risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    final_risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    initial_suspect_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    final_suspect_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    graph_reference: str | None = Field(
        default=None,
        max_length=500,
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None


# ============================================================
# INVESTIGATION RESPONSE
# ============================================================


class InvestigationResponse(InvestigationBase):
    """
    Schema returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    created_at: datetime | None = None

    updated_at: datetime | None = None

    deleted_at: datetime | None = None

    created_by: str | None = None

    updated_by: str | None = None

    case_number: str | None = None
    case_title: str | None = None
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.investigation_evidence import (
    InvestigationEvidenceRelation,
)


# ============================================================
# BASE SCHEMA
# ============================================================

class InvestigationEvidenceBase(BaseModel):
    """
    Common fields for an investigation-evidence relationship.
    """

    investigation_id: int = Field(
        ...,
        gt=0,
        description="ID of the investigation",
    )

    evidence_id: int = Field(
        ...,
        gt=0,
        description="ID of the evidence",
    )

    relation: InvestigationEvidenceRelation = Field(
        default=InvestigationEvidenceRelation.RELEVANT,
        description="How the evidence relates to the investigation",
    )

    notes: str | None = Field(
        default=None,
        description="Investigator notes about the relationship",
    )


# ============================================================
# CREATE
# ============================================================

class InvestigationEvidenceCreate(
    InvestigationEvidenceBase
):
    """
    Request schema for creating an investigation-evidence
    relationship.

    Example:

        {
            "investigation_id": 1,
            "evidence_id": 1,
            "relation": "primary",
            "notes": "CCTV footage directly supports the investigation."
        }
    """

    pass


# ============================================================
# UPDATE
# ============================================================

class InvestigationEvidenceUpdate(BaseModel):
    """
    Request schema for partially updating an
    investigation-evidence relationship.

    Only supplied fields are changed.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    relation: InvestigationEvidenceRelation | None = Field(
        default=None,
        description="Updated relationship type",
    )

    notes: str | None = Field(
        default=None,
        description="Updated investigator notes",
    )


# ============================================================
# RESPONSE
# ============================================================

class InvestigationEvidenceResponse(
    InvestigationEvidenceBase
):
    """
    Response schema returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    created_at: datetime

    updated_at: datetime

    deleted_at: datetime | None = None

    created_by: str | None = None

    updated_by: str | None = None
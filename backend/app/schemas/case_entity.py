from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.case_entity import CaseEntityRelation


# ============================================================
# BASE SCHEMA
# ============================================================


class CaseEntityBase(BaseModel):
    """
    Common fields for a case-entity relationship.
    """

    case_id: int = Field(
        ...,
        gt=0,
        description="ID of the case",
    )

    entity_id: int = Field(
        ...,
        gt=0,
        description="ID of the entity",
    )

    relation: CaseEntityRelation = Field(
        default=CaseEntityRelation.RELATED,
        description="How the entity is related to the case",
    )

    notes: str | None = Field(
        default=None,
        description="Additional notes about the relationship",
    )


# ============================================================
# CREATE
# ============================================================


class CaseEntityCreate(CaseEntityBase):
    """
    Request schema for creating a case-entity relationship.
    """

    pass


# ============================================================
# UPDATE
# ============================================================


class CaseEntityUpdate(BaseModel):
    """
    Request schema for partially updating a case-entity
    relationship.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    relation: CaseEntityRelation | None = None

    notes: str | None = None


# ============================================================
# RESPONSE
# ============================================================


class CaseEntityResponse(CaseEntityBase):
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
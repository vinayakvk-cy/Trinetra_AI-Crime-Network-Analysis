from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.entity_relationship import (
    EntityRelationshipType,
)


# ============================================================
# BASE SCHEMA
# ============================================================

class EntityRelationshipBase(BaseModel):
    """
    Common fields for an entity-to-entity relationship.
    """

    source_entity_id: int = Field(
        ...,
        gt=0,
        description="ID of the source entity",
    )

    target_entity_id: int = Field(
        ...,
        gt=0,
        description="ID of the target entity",
    )

    relationship_type: EntityRelationshipType = Field(
        ...,
        description="Type of relationship between the entities",
    )

    description: str | None = Field(
        default=None,
        description="Description of the relationship",
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in the relationship",
    )

    evidence_id: int | None = Field(
        default=None,
        gt=0,
        description="Evidence supporting this relationship",
    )


# ============================================================
# CREATE
# ============================================================

class EntityRelationshipCreate(
    EntityRelationshipBase
):
    """
    Schema for creating an entity relationship.
    """

    pass


# ============================================================
# UPDATE
# ============================================================

class EntityRelationshipUpdate(BaseModel):
    """
    Schema for partially updating an entity relationship.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    relationship_type: EntityRelationshipType | None = None

    description: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    evidence_id: int | None = Field(
        default=None,
        gt=0,
    )


# ============================================================
# RESPONSE
# ============================================================

class EntityRelationshipResponse(
    EntityRelationshipBase
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
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.entity import (
    EntitySource,
    EntityType,
)


# ============================================================
# BASE ENTITY SCHEMA
# ============================================================


class EntityBase(BaseModel):
    """
    Common fields shared by entity create and response schemas.
    """

    entity_type: EntityType = Field(
        default=EntityType.UNKNOWN,
        description="Type of entity",
    )

    name: str | None = Field(
        default=None,
        max_length=500,
        description="Original entity name or value",
    )

    normalized_name: str | None = Field(
        default=None,
        max_length=500,
        description="Normalized entity value",
    )

    external_id: str | None = Field(
        default=None,
        max_length=500,
        description="Identifier from the source system",
    )

    source: EntitySource = Field(
        default=EntitySource.UNKNOWN,
        description="Primary source of the entity",
    )

    source_reference: str | None = Field(
        default=None,
        max_length=500,
        description="Reference to the originating record",
    )

    description: str | None = Field(
        default=None,
        description="Entity description",
    )


# ============================================================
# CREATE ENTITY
# ============================================================


class EntityCreate(EntityBase):
    """
    Request schema for creating an entity.
    """

    extraction_method: str | None = Field(
        default=None,
        max_length=100,
        description="Method used to extract the entity",
    )

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="NLP extraction confidence",
    )

    linking_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Entity-linking confidence",
    )

    graph_node_id: str | None = Field(
        default=None,
        max_length=500,
        description="Neo4j graph node identifier",
    )

    risk_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Analytical risk score",
    )


# ============================================================
# UPDATE ENTITY
# ============================================================


class EntityUpdate(BaseModel):
    """
    Request schema for partially updating an entity.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    entity_type: EntityType | None = None

    name: str | None = Field(
        default=None,
        max_length=500,
    )

    normalized_name: str | None = Field(
        default=None,
        max_length=500,
    )

    external_id: str | None = Field(
        default=None,
        max_length=500,
    )

    source: EntitySource | None = None

    source_reference: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = None

    extraction_method: str | None = Field(
        default=None,
        max_length=100,
    )

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    linking_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    graph_node_id: str | None = Field(
        default=None,
        max_length=500,
    )

    risk_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )


# ============================================================
# ENTITY RESPONSE
# ============================================================


class EntityRead(EntityBase):
    """
    Response schema returned by the Entity API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    extraction_method: str | None = None

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    linking_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    graph_node_id: str | None = None

    risk_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    created_at: datetime

    updated_at: datetime

    deleted_at: datetime | None = None

    created_by: str | None = None

    updated_by: str | None = None


# ============================================================
# BACKWARD-COMPATIBLE RESPONSE NAME
# ============================================================

EntityResponse = EntityRead
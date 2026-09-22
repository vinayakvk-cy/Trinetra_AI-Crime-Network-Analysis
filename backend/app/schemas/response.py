"""
TRINETRA API Response Schemas
=============================

Common Pydantic response schemas used throughout the API.

These schemas provide a consistent response format for:

    - Cases
    - Entities
    - Evidence
    - Investigations
    - Ingestion
    - Graph analytics
    - Risk analysis
    - Reports
    - Local AI assistant
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


# ============================================================
# GENERIC TYPE
# ============================================================

T = TypeVar("T")


# ============================================================
# STANDARD API RESPONSE
# ============================================================


class APIResponse(BaseModel, Generic[T]):
    """
    Generic successful API response.

    Example:

        {
            "success": true,
            "message": "Case created successfully",
            "data": {...}
        }
    """

    success: bool = Field(
        default=True,
        description="Whether the operation was successful",
    )

    message: str = Field(
        default="Operation successful",
        description="Human-readable response message",
    )

    data: T | None = Field(
        default=None,
        description="Response payload",
    )


# ============================================================
# ERROR RESPONSE
# ============================================================


class ErrorResponse(BaseModel):
    """
    Standard API error response.

    Example:

        {
            "success": false,
            "message": "Case not found",
            "error_code": "CASE_NOT_FOUND",
            "details": {}
        }
    """

    success: bool = Field(
        default=False,
        description="Always false for an error response",
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
    )

    error_code: str | None = Field(
        default=None,
        description="Application-specific error code",
    )

    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error information",
    )


# ============================================================
# PAGINATION
# ============================================================


class PaginationMeta(BaseModel):
    """
    Metadata for paginated API responses.
    """

    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )

    page_size: int = Field(
        ...,
        ge=1,
        description="Number of records per page",
    )

    total: int = Field(
        ...,
        ge=0,
        description="Total number of records",
    )

    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )


# ============================================================
# PAGINATED RESPONSE
# ============================================================


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response.

    Example:

        {
            "success": true,
            "message": "Cases retrieved successfully",
            "data": [...],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total": 100,
                "total_pages": 5
            }
        }
    """

    success: bool = True

    message: str = "Records retrieved successfully"

    data: list[T] = Field(
        default_factory=list,
    )

    pagination: PaginationMeta


# ============================================================
# ANALYTICS RESPONSE
# ============================================================


class AnalyticsResponse(BaseModel):
    """
    Common response structure for analytical results.

    Used later by:

        graph analytics
        pattern detection
        risk engine
        similarity engine
    """

    success: bool = True

    message: str = "Analytics completed successfully"

    case_id: int | None = None

    risk_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Analytical risk score from 0 to 100",
    )

    confidence_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Analytical confidence score from 0 to 100. "
            "Not a legal determination."
        ),
    )

    risk_level: str | None = Field(
        default=None,
        description="Human-readable analytical risk level",
    )

    findings: list[str] = Field(
        default_factory=list,
        description="Analytical findings",
    )

    supporting_entities: list[int] = Field(
        default_factory=list,
        description="IDs of entities supporting the analytical result",
    )

    related_cases: list[int] = Field(
        default_factory=list,
        description="IDs of related/similar cases",
    )


# ============================================================
# INGESTION RESPONSE
# ============================================================


class IngestionResponse(BaseModel):
    """
    Response returned after a data ingestion operation.
    """

    success: bool = True

    message: str = "Data ingestion completed"

    source_type: str

    records_received: int = Field(
        default=0,
        ge=0,
    )

    records_processed: int = Field(
        default=0,
        ge=0,
    )

    records_rejected: int = Field(
        default=0,
        ge=0,
    )

    entities_created: int = Field(
        default=0,
        ge=0,
    )

    relationships_created: int = Field(
        default=0,
        ge=0,
    )

    errors: list[str] = Field(
        default_factory=list,
    )


# ============================================================
# GRAPH RESPONSE
# ============================================================


class GraphResponse(BaseModel):
    """
    Response structure for graph queries and graph analytics.
    """

    success: bool = True

    message: str = "Graph operation completed"

    case_id: int | None = None

    nodes: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    relationships: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    node_count: int = Field(
        default=0,
        ge=0,
    )

    relationship_count: int = Field(
        default=0,
        ge=0,
    )


# ============================================================
# ASSISTANT RESPONSE
# ============================================================


class AssistantResponse(BaseModel):
    """
    Response from the local AI assistant.

    The assistant should provide analytical assistance based
    on available case data and clearly distinguish generated
    suggestions from verified evidence.
    """

    success: bool = True

    message: str = "Assistant response generated"

    answer: str

    sources: list[str] = Field(
        default_factory=list,
    )

    related_entities: list[int] = Field(
        default_factory=list,
    )

    related_cases: list[int] = Field(
        default_factory=list,
    )

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


# ============================================================
# INVESTIGATION ACTION RESPONSE
# ============================================================


class InvestigationActionResponse(BaseModel):
    """
    Response structure for investigator actions/tasks.
    """

    success: bool = True

    message: str = "Investigation action recorded"

    investigation_id: int

    action_id: str | None = None

    action_type: str

    status: str

    result: str | None = None
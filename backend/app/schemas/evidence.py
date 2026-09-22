"""
TRINETRA Evidence API Schemas
=============================

Pydantic schemas for creating, updating, and returning evidence.

Database model:
    app/models/evidence.py

API schema:
    app/schemas/evidence.py

Evidence may originate from:

    - FIR
    - CDR
    - Transactions
    - GPS
    - Vehicles
    - Social media
    - Jail records
    - Forensic analysis
    - Post-mortem reports
    - Documents
    - Images
    - Videos
    - Audio
    - Other digital/physical sources
"""

from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.evidence import (
    EvidenceStatus,
    EvidenceType,
)


# ============================================================
# BASE EVIDENCE SCHEMA
# ============================================================


class EvidenceBase(BaseModel):
    """
    Common fields shared by evidence request schemas.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable evidence title",
    )

    description: str | None = Field(
        default=None,
        description="Description of the evidence",
    )

    evidence_type: EvidenceType = Field(
        ...,
        description="Type/category of evidence",
    )

    status: EvidenceStatus = Field(
        default=EvidenceStatus.RECEIVED,
        description="Current evidence processing status",
    )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    source_type: str | None = Field(
        default=None,
        max_length=100,
        description="Source system/type",
    )

    source_reference: str | None = Field(
        default=None,
        max_length=500,
        description="Reference to the original source record",
    )

    source_file: str | None = Field(
        default=None,
        max_length=500,
        description="Original source file",
    )


# ============================================================
# CREATE EVIDENCE
# ============================================================


class EvidenceCreate(EvidenceBase):
    """
    Request schema for creating evidence.

    The case_id associates the evidence with a case.
    """

    case_id: int = Field(
        ...,
        gt=0,
        description="ID of the case associated with the evidence",
    )

    evidence_number: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique evidence number",
    )

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    file_name: str | None = Field(
        default=None,
        max_length=500,
        description="Evidence file name",
    )

    file_path: str | None = Field(
        default=None,
        max_length=1000,
        description="Storage path for the evidence",
    )

    file_hash: str | None = Field(
        default=None,
        max_length=128,
        description="Cryptographic hash of the evidence file",
    )

    mime_type: str | None = Field(
        default=None,
        max_length=150,
        description="MIME type of the evidence file",
    )

    file_size: int | None = Field(
        default=None,
        ge=0,
        description="Evidence file size in bytes",
    )

    # --------------------------------------------------------
    # NLP / TEXT EXTRACTION
    # --------------------------------------------------------

    extracted_text: str | None = Field(
        default=None,
        description="Text extracted from the evidence",
    )

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence of text/entity extraction",
    )

    # --------------------------------------------------------
    # FORENSIC ANALYSIS
    # --------------------------------------------------------

    forensic_result: str | None = Field(
        default=None,
        description="Forensic analysis result",
    )

    forensic_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence of forensic analysis",
    )

    # --------------------------------------------------------
    # GRAPH
    # --------------------------------------------------------

    graph_node_id: str | None = Field(
        default=None,
        max_length=500,
        description="Neo4j graph node identifier",
    )


# ============================================================
# UPDATE EVIDENCE
# ============================================================


class EvidenceUpdate(BaseModel):
    """
    Request schema for partially updating evidence.

    All fields are optional.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    evidence_type: EvidenceType | None = None

    status: EvidenceStatus | None = None

    source_type: str | None = Field(
        default=None,
        max_length=100,
    )

    source_reference: str | None = Field(
        default=None,
        max_length=500,
    )

    source_file: str | None = Field(
        default=None,
        max_length=500,
    )

    file_name: str | None = Field(
        default=None,
        max_length=500,
    )

    file_path: str | None = Field(
        default=None,
        max_length=1000,
    )

    file_hash: str | None = Field(
        default=None,
        max_length=128,
    )

    mime_type: str | None = Field(
        default=None,
        max_length=150,
    )

    file_size: int | None = Field(
        default=None,
        ge=0,
    )

    extracted_text: str | None = None

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    forensic_result: str | None = None

    forensic_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    graph_node_id: str | None = Field(
        default=None,
        max_length=500,
    )


# ============================================================
# EVIDENCE RESPONSE
# ============================================================


class EvidenceRead(EvidenceBase):
    """
    Response schema returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    case_id: int

    evidence_number: str

    file_name: str | None = None

    file_path: str | None = None

    file_hash: str | None = None

    mime_type: str | None = None

    file_size: int | None = None

    extracted_text: str | None = None

    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    forensic_result: str | None = None

    forensic_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    graph_node_id: str | None = None

    # Canonical intelligence derived from the stored evidence
    # record and persisted NLP relationships.
    extracted_entities: list[dict] = Field(default_factory=list)
    extracted_relationships: list[dict] = Field(default_factory=list)
    ingestion: dict | None = None

    created_at: datetime

    updated_at: datetime

# ============================================================
# BACKWARD-COMPATIBLE RESPONSE NAME
# ============================================================

EvidenceResponse = EvidenceRead
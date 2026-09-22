from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# INTELLIGENCE SEVERITY
# ============================================================


class IntelligenceSeverity(str, Enum):
    """
    Severity assigned to an AI-generated intelligence finding.
    """

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    CRITICAL = "critical"


# ============================================================
# INTELLIGENCE FINDING
# ============================================================


class IntelligenceFinding(BaseModel):
    """
    Represents one finding produced by the AI intelligence layer.

    Example:

        Repeated communication detected between two entities.
    """

    title: str = Field(
        ...,
        description="Short title of the intelligence finding.",
    )

    description: str = Field(
        ...,
        description="Detailed explanation of the finding.",
    )

    severity: IntelligenceSeverity = Field(
        default=IntelligenceSeverity.LOW,
        description="Severity of the finding.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence in this finding.",
    )

    supporting_entity_ids: list[int] = Field(
        default_factory=list,
        description="Entities supporting this finding.",
    )

    supporting_evidence_ids: list[int] = Field(
        default_factory=list,
        description="Evidence records supporting this finding.",
    )

    supporting_relationship_ids: list[int] = Field(
        default_factory=list,
        description="Entity relationships supporting this finding.",
    )


# ============================================================
# RISK ASSESSMENT
# ============================================================


class IntelligenceRiskAssessment(BaseModel):
    """
    Represents the AI-generated risk assessment.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall risk score.",
    )

    severity: IntelligenceSeverity = Field(
        default=IntelligenceSeverity.LOW,
        description="Risk severity.",
    )

    explanation: str = Field(
        ...,
        description="Explanation for the calculated risk.",
    )


# ============================================================
# INTELLIGENCE RESULT
# ============================================================


class IntelligenceResult(BaseModel):
    """
    Complete output produced by the AI intelligence engine.

    This is the object that will eventually be returned by:

        AI Intelligence Engine
                ↓
        IntelligenceResult
    """

    investigation_id: int = Field(
        ...,
        gt=0,
        description="Investigation being analyzed.",
    )

    findings: list[IntelligenceFinding] = Field(
        default_factory=list,
        description="AI-generated intelligence findings.",
    )

    risk_assessment: IntelligenceRiskAssessment | None = Field(
        default=None,
        description="Overall risk assessment.",
    )

    summary: str = Field(
        default="",
        description="Overall AI-generated intelligence summary.",
    )

    overall_confidence: float = Field(
    default=0.0,
    ge=0.0,
    le=1.0,
    description="Overall confidence in the intelligence analysis.",
)

    analyzed_entity_count: int = Field(
        default=0,
        ge=0,
        description="Number of entities analyzed.",
    )

    analyzed_evidence_count: int = Field(
        default=0,
        ge=0,
        description="Number of evidence records analyzed.",
    )

    analyzed_relationship_count: int = Field(
        default=0,
        ge=0,
        description="Number of relationships analyzed.",
    )
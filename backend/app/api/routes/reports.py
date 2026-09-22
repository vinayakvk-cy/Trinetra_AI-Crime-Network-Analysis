"""
TRINETRA Reports API
====================

FastAPI routes for investigation reporting.

Responsibilities
----------------
- Generate intelligence reports
- Generate criminal-documentary reports
- Retrieve report output
- Return structured report metadata

The route layer does not contain report-generation logic.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.config import settings
from app.graph.neo4j_client import Neo4jClient
from app.reports.intelligence_report import IntelligenceReportGenerator
from app.reports.criminal_documentary import CriminalDocumentaryGenerator


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class ReportRequest(BaseModel):
    """
    Common report-generation request.
    """

    investigation_id: int

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    include_evidence: bool = True

    include_entities: bool = True

    include_relationships: bool = True

    include_analytics: bool = True

    include_timeline: bool = True


class IntelligenceReportRequest(
    ReportRequest
):
    """
    Intelligence report request.
    """

    classification: str = "internal"

    summary: str | None = None


class DocumentaryReportRequest(
    ReportRequest
):
    """
    Criminal-documentary report request.
    """

    narrative_style: str = "investigative"

    include_narrative: bool = True


# ============================================================
# INTELLIGENCE REPORT
# ============================================================


@router.post(
    "/intelligence",
)
def generate_intelligence_report(
    payload: IntelligenceReportRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate an intelligence report.
    """

    try:

        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        generator = IntelligenceReportGenerator(
            session=db,
            neo4j_client=neo4j_client,
        )

        result = generator.generate(
            investigation_id=(
                payload.investigation_id
            ),
            title=payload.title,
            classification=(
                payload.classification
            ),
            summary=payload.summary,
            include_evidence=(
                payload.include_evidence
            ),
            include_entities=(
                payload.include_entities
            ),
            include_relationships=(
                payload.include_relationships
            ),
            include_analytics=(
                payload.include_analytics
            ),
            include_timeline=(
                payload.include_timeline
            ),
        )

        return {
            "success": True,
            "report_type": "intelligence",
            "report": _serialize(
                result
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except AttributeError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The intelligence report generator "
                f"does not expose the expected method: {exc}"
            ),
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Intelligence report generation failed: "
                f"{exc}"
            ),
        )


# ============================================================
# CRIMINAL DOCUMENTARY
# ============================================================


@router.post(
    "/documentary",
)
def generate_documentary_report(
    payload: DocumentaryReportRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate an investigative documentary-style report.

    The documentary generator is investigation-scoped and
    obtains its source material from the investigation itself.
    """

    try:
        generator = CriminalDocumentaryGenerator(db)

        result = generator.generate(
            investigation_id=payload.investigation_id,
            include_actions=True,
            include_notes=payload.include_narrative,
        )

        return {
            "success": True,
            "report_type": "criminal_documentary",
            "report": _serialize(result),
        }

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Documentary report generation failed: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# REPORT PREVIEW
# ============================================================


@router.post(
    "/preview",
)
def preview_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate a lightweight report preview.

    This endpoint is useful for the frontend before committing
    to a full report.
    """

    try:

        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        generator = IntelligenceReportGenerator(
            session=db,
            neo4j_client=neo4j_client,
        )

        result = generator.generate(
            investigation_id=(
                payload.investigation_id
            ),
            title=payload.title,
            classification="preview",
            summary=None,
            include_evidence=(
                payload.include_evidence
            ),
            include_entities=(
                payload.include_entities
            ),
            include_relationships=(
                payload.include_relationships
            ),
            include_analytics=(
                payload.include_analytics
            ),
            include_timeline=(
                payload.include_timeline
            ),
        )

        serialized = _serialize(
            result
        )

        return {
            "success": True,
            "report_type": "preview",
            "report": serialized,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report preview failed: {exc}",
        )


# ============================================================
# REPORT TYPES
# ============================================================


@router.get(
    "/types",
)
def list_report_types() -> dict[str, Any]:
    """
    Return supported report types.
    """

    return {
        "success": True,
        "types": [
            {
                "id": "intelligence",
                "name": "Intelligence Report",
                "description": (
                    "Structured analytical investigation report."
                ),
            },
            {
                "id": "criminal_documentary",
                "name": "Criminal Documentary",
                "description": (
                    "Narrative investigative report built "
                    "from available case information."
                ),
            },
            {
                "id": "preview",
                "name": "Report Preview",
                "description": (
                    "Lightweight report preview."
                ),
            },
        ],
    }


# ============================================================
# SERIALIZATION
# ============================================================


def _serialize(
    value: Any,
) -> Any:
    """
    Convert report objects into JSON-compatible structures.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _serialize(item)
            for item in value
        ]

    if hasattr(
        value,
        "model_dump",
    ):
        return _serialize(
            value.model_dump()
        )

    if hasattr(
        value,
        "__table__",
    ):
        return {
            column.name: _serialize(
                getattr(
                    value,
                    column.name,
                )
            )
            for column
            in value.__table__.columns
        }

    if hasattr(
        value,
        "__dict__",
    ):
        return {
            key: _serialize(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)
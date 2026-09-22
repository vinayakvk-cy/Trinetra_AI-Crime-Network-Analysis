from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analytics.graph_algorithms import GraphAnalytics
from app.analytics.graph_analytics import GraphAnalyticsEngine
from app.analytics.pattern_detector import PatternDetector
from app.analytics.risk_engine import RiskEngine
from app.analytics.similarity_engine import SimilarityEngine
from app.core.config import settings
from app.db.database import get_db
from app.graph.graph_queries import GraphQueries
from app.graph.neo4j_client import Neo4jClient
from app.models.case import Case
from app.models.entity import Entity
from app.models.investigation import Investigation


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class EntityAnalysisRequest(BaseModel):
    """
    Entity used as the starting point for analysis.
    """

    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    entity_value: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )


class SimilarityRequest(BaseModel):
    """
    Request for entity similarity analysis.
    """

    source_entity_id: int

    target_entity_id: int | None = None

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class RiskRequest(BaseModel):
    """
    Request for risk analysis.

    Either entity_id or investigation_id must be supplied.
    """

    entity_id: int | None = None

    investigation_id: int | None = None


class PatternRequest(BaseModel):
    """
    Request for pattern detection.

    The current PatternDetector implementation exposes
    detect_all(), so the supplied identifiers are retained
    for API compatibility but the detector currently runs
    the complete pattern analysis.
    """

    investigation_id: int | None = None

    entity_id: int | None = None


# ============================================================
# NEO4J DEPENDENCY
# ============================================================


def get_neo4j_client() -> Neo4jClient:
    """
    Create a configured Neo4j client for analytics operations.
    """

    return Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )


# ============================================================
# GRAPH CENTRALITY
# ============================================================


@router.get(
    "/graph/centrality",
)
def graph_centrality(
    limit: int = 20,
    db: Session = Depends(get_db),
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Calculate graph-centrality information.
    """

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500.",
        )

    try:
        analytics = GraphAnalytics(
            client
        )

        result = analytics.top_connected_entities(
            limit=limit
        )

        # Centrality is computed in Neo4j, while the rest of the
        # application uses canonical SQL entity IDs. Enrich the
        # live graph rows so downstream risk/similarity actions
        # can safely resolve the selected entity.
        for row in result:
            entity = (
                db.query(Entity)
                .filter(
                    Entity.name == row.get("value"),
                    Entity.deleted_at.is_(None),
                )
                .first()
            )

            if entity is not None:
                row["entity_id"] = entity.id

        return {
            "success": True,
            "analysis": "centrality",
            "results": result,
        }

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Graph centrality analytics are not "
                "available in the current implementation: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Centrality analysis failed: {exc}"
            ),
        ) from exc


# ============================================================
# GRAPH CONNECTIVITY
# ============================================================


@router.get(
    "/graph/connectivity",
)
def graph_connectivity(
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Analyze graph connectivity.
    """

    try:
        analytics = GraphAnalytics(
            client
        )

        result = analytics.bridge_analysis(
            limit=20
        )

        return {
            "success": True,
            "analysis": "connectivity",
            "results": result,
        }

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Graph connectivity analytics are not "
                "available in the current implementation: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Connectivity analysis failed: {exc}"
            ),
        ) from exc


# ============================================================
# ENTITY PATTERNS
# ============================================================


@router.post(
    "/patterns",
)
def detect_patterns(
    payload: PatternRequest,
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Detect potentially relevant investigation patterns.
    """

    try:
        detector = PatternDetector(
            client
        )

        result = detector.detect_all(
            limit=20
        )

        return {
            "success": True,
            "analysis": "patterns",
            "results": result,
        }

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "PatternDetector.detect_all() is "
                "not available in the current implementation: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Pattern detection failed: {exc}"
            ),
        ) from exc


# ============================================================
# RISK
# ============================================================


@router.post(
    "/risk",
)
def calculate_risk(
    payload: RiskRequest,
    db: Session = Depends(get_db),
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Calculate analytical risk indicators.

    Risk output is an analytical signal only and does not
    constitute a determination of guilt or wrongdoing.

    The current RiskEngine exposes:
        - assess_entity()
        - assess_case()

    It does not expose calculate().
    """

    if (
        payload.entity_id is None
        and payload.investigation_id is None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Either entity_id or investigation_id "
                "must be supplied."
            ),
        )

    if (
        payload.entity_id is not None
        and payload.investigation_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Supply either entity_id or "
                "investigation_id, not both."
            ),
        )

    try:
        engine = RiskEngine(
            client
        )

        # ----------------------------------------------------
        # ENTITY RISK
        # ----------------------------------------------------

        if payload.entity_id is not None:
            entity = (
                db.query(Entity)
                .filter(
                    Entity.id == payload.entity_id,
                    Entity.deleted_at.is_(None),
                )
                .first()
            )

            if entity is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Entity {payload.entity_id} not found.",
                )

            entity_type = getattr(
                entity.entity_type,
                "value",
                entity.entity_type,
            )

            assessment = engine.assess_entity(
                entity_type=str(entity_type),
                value=entity.name,
            )

            result = (
                assessment.to_dict()
                if assessment is not None
                else {
                    "entity_type": str(entity_type),
                    "entity_value": entity.name,
                    "score": 0.0,
                    "level": "unknown",
                    "signals": [],
                    "patterns": [],
                    "explanation": (
                        "No graph profile was found for this entity."
                    ),
                }
            )

            return {
                "success": True,
                "analysis": "entity_risk",
                "entity_id": payload.entity_id,
                "result": result,
            }

        # ----------------------------------------------------
        # INVESTIGATION / CASE RISK
        # ----------------------------------------------------

        investigation = (
            db.query(Investigation)
            .filter(
                Investigation.id
                == payload.investigation_id
            )
            .first()
        )

        if investigation is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Investigation "
                    f"{payload.investigation_id} "
                    "not found."
                ),
            )

        case = (
            db.query(Case)
            .filter(
                Case.id
                == investigation.case_id
            )
            .first()
        )

        if case is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Case {investigation.case_id} "
                    "not found."
                ),
            )

        assessment = engine.assess_case(
            case_value=case.case_number
        )

        result = (
            assessment.to_dict()
            if assessment is not None
            else {
                "entity_type": "CASE",
                "entity_value": case.case_number,
                "score": 0.0,
                "level": "unknown",
                "signals": [],
                "patterns": [],
                "explanation": (
                    "No Neo4j graph entities were found "
                    "for this case."
                ),
            }
        )

        return {
            "success": True,
            "analysis": "risk",
            "results": result,
            "disclaimer": (
                "Risk indicators are analytical signals "
                "and must not be treated as determinations "
                "of guilt."
            ),
        }

    except HTTPException:
        raise

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "RiskEngine assessment is not "
                "available in the current implementation: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Risk analysis failed: {exc}"
            ),
        ) from exc


# ============================================================
# ENTITY SIMILARITY
# ============================================================


@router.post(
    "/similarity",
)
def entity_similarity(
    payload: SimilarityRequest,
    db: Session = Depends(get_db),
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Calculate similarity between entities or retrieve
    the closest matching entities.
    """

    if payload.source_entity_id < 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "source_entity_id must be greater than 0."
            ),
        )

    if (
        payload.target_entity_id is not None
        and payload.target_entity_id < 1
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "target_entity_id must be greater than 0."
            ),
        )

    try:
        engine = SimilarityEngine(
            client
        )

        source_entity = (
            db.query(Entity)
            .filter(
                Entity.id == payload.source_entity_id,
                Entity.deleted_at.is_(None),
            )
            .first()
        )

        if source_entity is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Source entity "
                    f"{payload.source_entity_id} "
                    "not found."
                ),
            )

        source_type = getattr(
            source_entity.entity_type,
            "value",
            source_entity.entity_type,
        )

        if payload.target_entity_id is not None:
            target_entity = (
                db.query(Entity)
                .filter(
                    Entity.id == payload.target_entity_id,
                    Entity.deleted_at.is_(None),
                )
                .first()
            )

            if target_entity is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Target entity "
                        f"{payload.target_entity_id} "
                        "not found."
                    ),
                )

            target_type = getattr(
                target_entity.entity_type,
                "value",
                target_entity.entity_type,
            )

            result = engine.compare_entities(
                source_type=str(source_type),
                source_value=source_entity.name,
                target_type=str(target_type),
                target_value=target_entity.name,
            )

        else:
            result = engine.find_similar_entities(
                entity_type=str(source_type),
                value=source_entity.name,
                limit=payload.limit,
            )

        return {
            "success": True,
            "analysis": "similarity",
            "results": result,
        }

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "The requested similarity operation "
                "is not available in the current "
                "implementation: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Similarity analysis failed: {exc}"
            ),
        ) from exc


# ============================================================
# INVESTIGATION SUMMARY
# ============================================================


@router.get(
    "/investigations/{investigation_id}/summary",
)
def investigation_analytics_summary(
    investigation_id: int,
    db: Session = Depends(get_db),
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Return a combined analytical overview of an investigation.

    Flow:

        investigation_id
            ↓
        Investigation
            ↓
        case_id
            ↓
        Case
            ↓
        case_number
            ↓
        graph / pattern / risk analytics
    """

    if investigation_id < 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "investigation_id must be greater than 0."
            ),
        )

    try:
        # ====================================================
        # RELATIONAL INVESTIGATION
        # ====================================================

        investigation = (
            db.query(Investigation)
            .filter(
                Investigation.id
                == investigation_id
            )
            .first()
        )

        if investigation is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Investigation "
                    f"{investigation_id} "
                    "not found."
                ),
            )

        # ====================================================
        # RELATIONAL CASE
        # ====================================================

        case = (
            db.query(Case)
            .filter(
                Case.id
                == investigation.case_id
            )
            .first()
        )

        if case is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Case {investigation.case_id} "
                    "not found."
                ),
            )

        # ====================================================
        # GRAPH ANALYTICS
        # ====================================================

        graph_queries = GraphQueries(
            client
        )

        graph = GraphAnalyticsEngine(
            graph_queries
        )

        graph_result = graph.analyze_case(
            case.case_number
        ).to_dict()

        # ====================================================
        # PATTERN ANALYTICS
        # ====================================================

        patterns = PatternDetector(
            client
        )

        pattern_result = patterns.detect_all(
            limit=20
        )

        # ====================================================
        # RISK ANALYTICS
        # ====================================================

        risk = RiskEngine(
            client
        )

        risk_assessment = risk.assess_case(
            case_value=case.case_number
        )

        risk_result = (
            risk_assessment.to_dict()
            if risk_assessment is not None
            else {
                "entity_type": "CASE",
                "entity_value": case.case_number,
                "score": 0.0,
                "level": "unknown",
                "signals": [],
                "patterns": [],
                "explanation": (
                    "No Neo4j graph entities were found "
                    "for this case."
                ),
            }
        )

        # ====================================================
        # COMBINED RESPONSE
        # ====================================================

        return {
            "success": True,
            "investigation_id": investigation_id,
            "investigation": {
                "id": investigation.id,
                "investigation_number": (
                    investigation.investigation_number
                ),
                "title": investigation.title,
                "case_id": investigation.case_id,
            },
            "case": {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "status": case.status,
                "priority": case.priority,
            },
            "graph": graph_result,
            "patterns": pattern_result,
            "risk": risk_result,
            "disclaimer": (
                "Analytical results are investigative "
                "signals and require verification against "
                "underlying evidence."
            ),
        }

    except HTTPException:
        raise

    except AttributeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "One or more analytics methods are not "
                "available: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Investigation analytics failed: "
                f"{exc}"
            ),
        ) from exc
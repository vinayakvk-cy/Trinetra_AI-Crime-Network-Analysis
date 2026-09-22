"""
TRINETRA Graph API
==================

FastAPI routes for graph operations.

Responsibilities
----------------
- Query entity relationships
- Retrieve entity neighborhoods
- Execute predefined graph queries
- Build graph relationships
- Return graph data for the frontend

The API does not contain graph business logic. It delegates
graph operations to the graph layer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph.neo4j_client import Neo4jClient
from app.graph.graph_builder import GraphBuilder
from app.graph.graph_queries import GraphQueries
from app.graph.graph_algorithms import GraphAlgorithms
from app.nlp.entity_extractor import EntityCandidate
from app.nlp.relation_extractor import RelationCandidate


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/graph",
    tags=["Graph"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class GraphEntityRequest(BaseModel):
    """
    Entity used as the starting point for graph exploration.
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

    depth: int = Field(
        default=1,
        ge=1,
        le=5,
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )


class GraphRelationshipRequest(BaseModel):
    """
    Request to create a graph relationship.
    """

    source_type: str
    source_value: str

    relationship_type: str

    target_type: str
    target_value: str

    properties: dict[str, Any] = Field(
        default_factory=dict
    )


class GraphQueryRequest(BaseModel):
    """
    Generic predefined graph query request.
    """

    query_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# DEPENDENCY
# ============================================================


def get_neo4j_client():
    return Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )


# ============================================================
# GRAPH HEALTH
# ============================================================


@router.get(
    "/health",
)
def graph_health(
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Check Neo4j connectivity.
    """

    try:

        healthy = client.health_check()

        return {
            "success": True,
            "neo4j": bool(healthy),
        }

    except Exception as exc:

        return {
            "success": False,
            "neo4j": False,
            "error": str(exc),
        }


# ============================================================
# ENTITY NEIGHBORHOOD
# ============================================================


@router.post("/neighborhood")
def get_neighborhood(
    payload: GraphEntityRequest,
    client: Neo4jClient = Depends(get_neo4j_client),
) -> dict[str, Any]:
    try:
        entity_type = payload.entity_type.strip().lower()
        entity_value = payload.entity_value.strip().lower()

        query = """
        MATCH (start:Entity)
        WHERE toLower(start.entity_type) = $entity_type
          AND (
              toLower(start.normalized_value) = $entity_value
              OR toLower(start.value) = $entity_value
          )

        MATCH path = (start)-[*1..5]-(neighbor)
        WHERE length(path) <= $depth

        RETURN DISTINCT
            elementId(start) AS start_id,
            start.entity_type AS start_type,
            start.value AS start_value,
            elementId(neighbor) AS neighbor_id,
            neighbor.entity_type AS neighbor_type,
            neighbor.value AS neighbor_value,
            length(path) AS path_depth,
            [
                rel IN relationships(path) |
                {
                    relationship_type: type(rel),
                    confidence: rel.confidence,
                    evidence_text: rel.evidence_text,
                    source_field: rel.source_field
                }
            ] AS relationships
        ORDER BY path_depth
        LIMIT $limit
        """

        records = client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "entity_value": entity_value.strip().lower(),
                "depth": payload.depth,
                "limit": payload.limit,
            },
        )

        results = [dict(record) for record in records]

        return {
            "success": True,
            "entity": {
                "type": payload.entity_type,
                "value": payload.entity_value,
            },
            "depth": payload.depth,
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph query failed: {exc}",
        )


# ============================================================
# ENTITY RELATIONSHIPS
# ============================================================


@router.get(
    "/relationships",
)
def get_relationships(
    entity_type: str,
    entity_value: str,
    limit: int = 100,
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Retrieve direct relationships for an entity.
    """

    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 1000.",
        )

    query = """
MATCH (n:Entity)
WHERE n.entity_type = $entity_type
  AND (
      n.normalized_value = $entity_value
      OR toLower(n.value) = $entity_value
  )

MATCH (n)-[r]-(neighbor)

RETURN
    elementId(n) AS source_id,
    n.entity_type AS source_type,
    n.value AS source_value,
    type(r) AS relationship_type,
    elementId(neighbor) AS target_id,
    neighbor.entity_type AS target_type,
    neighbor.value AS target_value,

    r.confidence AS confidence,
    r.evidence_text AS evidence_text,
    r.source_field AS source_field

LIMIT $limit
"""

    try:

        records = client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "entity_value": (
                    entity_value
                    .strip()
                    .lower()
                ),
                "limit": limit,
            },
        )

        return {
            "success": True,
            "count": len(records),
            "relationships": [
                dict(record)
                for record in records
            ],
        }

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph query failed: {exc}",
        )


# ============================================================
# CREATE RELATIONSHIP
# ============================================================


@router.post(
    "/relationships",
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    payload: GraphRelationshipRequest,
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Create a relationship between two entities.

    Relationship creation is delegated to GraphBuilder.
    """

    try:

        builder = GraphBuilder(
            client
        )

        source_entity = EntityCandidate(
            entity_type=payload.source_type,
            value=payload.source_value,
            normalized_value=payload.source_value.strip().lower(),
        )

        target_entity = EntityCandidate(
            entity_type=payload.target_type,
            value=payload.target_value,
            normalized_value=payload.target_value.strip().lower(),
        )

        properties = payload.properties or {}

        relation = RelationCandidate(
            relation_type=payload.relationship_type,
            source_entity=source_entity,
            target_entity=target_entity,
            confidence=float(
                properties.get("confidence", 1.0)
            ),
            evidence_text=properties.get("evidence_text"),
            source_field=properties.get("source_field"),
            metadata=properties,
        )

        result = builder.create_relationship(relation)

        return {
            "success": True,
            "result": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Relationship creation failed: {exc}",
        )


# ============================================================
# PREDEFINED GRAPH QUERY
# ============================================================


@router.post(
    "/query",
)
def execute_graph_query(
    payload: GraphQueryRequest,
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Execute a predefined graph query.

    Only queries exposed by GraphQueries are allowed.
    Arbitrary Cypher is intentionally not accepted through
    the API.
    """

    try:

        queries = GraphQueries(
            client
        )

        method = getattr(
            queries,
            payload.query_name,
            None,
        )

        if method is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Unknown graph query: "
                    f"{payload.query_name}"
                ),
            )

        if (
            not callable(method)
            or payload.query_name.startswith("_")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid graph query.",
            )

        result = method(
            **payload.parameters
        )

        return {
            "success": True,
            "query": payload.query_name,
            "results": result,
        }

    except HTTPException:
        raise

    except TypeError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query parameters: {exc}",
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph query failed: {exc}",
        )


# ============================================================
# SHORTEST PATH
# ============================================================


@router.get(
    "/shortest-path",
)
def shortest_path(
    source_type: str,
    source_value: str,
    target_type: str,
    target_value: str,
    max_depth: int = 6,
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Find a shortest graph path between two entities.
    """

    if max_depth < 1 or max_depth > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "max_depth must be between "
                "1 and 10."
            ),
        )

    try:

        algorithms = GraphAlgorithms(
            client
        )

        result = algorithms.shortest_path(
            source_type=source_type,
            source_value=source_value,
            target_type=target_type,
            target_value=target_value,
            max_depth=max_depth,
        )

        return {
            "success": True,
            "source": {
                "type": source_type,
                "value": source_value,
            },
            "target": {
                "type": target_type,
                "value": target_value,
            },
            "result": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Path analysis failed: {exc}",
        )


# ============================================================
# GRAPH STATISTICS
# ============================================================


@router.get(
    "/stats",
)
def graph_stats(
    client: Neo4jClient = Depends(
        get_neo4j_client
    ),
) -> dict[str, Any]:
    """
    Return basic graph statistics.
    """

    try:

        query = """
        MATCH (n)
        WITH count(n) AS nodes

        OPTIONAL MATCH ()-[r]->()

        RETURN
            nodes,
            count(r) AS relationships
        """

        records = client.execute_read(
            query
        )

        if not records:
            return {
                "success": True,
                "nodes": 0,
                "relationships": 0,
            }

        record = records[0]

        return {
            "success": True,
            "nodes": record.get(
                "nodes",
                0,
            ),
            "relationships": record.get(
                "relationships",
                0,
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve graph statistics: {exc}",
        )
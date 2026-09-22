"""
TRINETRA Similarity Engine
==========================

Entity similarity analysis based on shared graph structure.

Responsibilities
----------------
- Compare two entities
- Find shared neighboring entities
- Calculate Jaccard similarity
- Find similar entities
- Explain why two entities are considered similar

This module does NOT:
- Determine guilt
- Make legal conclusions
- Modify graph data
- Extract entities
- Assign criminal risk by itself
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.graph.graph_queries import GraphQueries
from app.graph.neo4j_client import Neo4jClient


# ============================================================
# SIMILARITY RESULT
# ============================================================


@dataclass
class SimilarityResult:
    """
    Result of comparing two entities.
    """

    source_type: str

    source_value: str

    target_type: str

    target_value: str

    score: float

    method: str

    shared_entities: list[dict[str, Any]] = field(
        default_factory=list
    )

    explanation: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result into an API-friendly dictionary.
        """

        return {
            "source_type": self.source_type,
            "source_value": self.source_value,
            "target_type": self.target_type,
            "target_value": self.target_value,
            "score": self.score,
            "method": self.method,
            "shared_entities": self.shared_entities,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


# ============================================================
# SIMILARITY ENGINE
# ============================================================


class SimilarityEngine:
    """
    Graph-based entity similarity service.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:

        self.client = client

        self.queries = GraphQueries(
            client
        )

    # ========================================================
    # ENTITY NEIGHBORS
    # ========================================================

    def get_neighbor_keys(
        self,
        entity_type: str,
        value: str,
        depth: int = 1,
    ) -> set[str]:
        """
        Return normalized keys representing an entity's
        graph neighborhood.
        """

        neighbors = self.queries.get_neighbors(
            entity_type=entity_type,
            value=value,
            depth=depth,
        )

        keys: set[str] = set()

        for neighbor in neighbors:

            neighbor_type = neighbor.get(
                "entity_type"
            )

            neighbor_value = neighbor.get(
                "value"
            )

            if not neighbor_type or not neighbor_value:
                continue

            key = (
                f"{neighbor_type}:"
                f"{str(neighbor_value).strip().lower()}"
            )

            keys.add(key)

        return keys

    # ========================================================
    # JACCARD SIMILARITY
    # ========================================================

    @staticmethod
    def jaccard_similarity(
        first: set[str],
        second: set[str],
    ) -> float:
        """
        Calculate Jaccard similarity:

            intersection / union
        """

        if not first and not second:
            return 0.0

        union = first | second

        if not union:
            return 0.0

        intersection = first & second

        return round(
            len(intersection)
            / len(union),
            4,
        )

    # ========================================================
    # COMPARE ENTITIES
    # ========================================================

    def compare_entities(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        depth: int = 1,
    ) -> SimilarityResult:
        """
        Compare two entities based on shared graph neighbors.
        """

        source_neighbors = (
            self.get_neighbor_keys(
                entity_type=source_type,
                value=source_value,
                depth=depth,
            )
        )

        target_neighbors = (
            self.get_neighbor_keys(
                entity_type=target_type,
                value=target_value,
                depth=depth,
            )
        )

        shared_keys = (
            source_neighbors
            & target_neighbors
        )

        score = self.jaccard_similarity(
            source_neighbors,
            target_neighbors,
        )

        shared_entities = (
            self._parse_entity_keys(
                shared_keys
            )
        )

        explanation = self._build_explanation(
            source_type=source_type,
            source_value=source_value,
            target_type=target_type,
            target_value=target_value,
            score=score,
            shared_count=len(
                shared_entities
            ),
        )

        return SimilarityResult(
            source_type=source_type,
            source_value=source_value,
            target_type=target_type,
            target_value=target_value,
            score=score,
            method="jaccard_shared_neighbors",
            shared_entities=shared_entities,
            explanation=explanation,
            metadata={
                "source_neighbor_count": len(
                    source_neighbors
                ),
                "target_neighbor_count": len(
                    target_neighbors
                ),
                "shared_neighbor_count": len(
                    shared_entities
                ),
                "depth": depth,
            },
        )

    # ========================================================
    # SIMILAR ENTITIES
    # ========================================================

    def find_similar_entities(
        self,
        entity_type: str,
        value: str,
        candidate_type: str | None = None,
        limit: int = 20,
        minimum_score: float = 0.20,
    ) -> list[SimilarityResult]:
        """
        Find entities structurally similar to a target entity.

        Candidates are obtained from the graph and compared
        using shared-neighbor Jaccard similarity.
        """

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        if limit > 100:
            raise ValueError(
                "Limit cannot exceed 100."
            )

        minimum_score = max(
            0.0,
            min(
                float(minimum_score),
                1.0,
            ),
        )

        candidates = (
            self._candidate_entities(
                entity_type=entity_type,
                value=value,
                candidate_type=candidate_type,
                limit=limit * 5,
            )
        )

        results: list[
            SimilarityResult
        ] = []

        for candidate in candidates:

            candidate_value = candidate.get(
                "value"
            )

            candidate_entity_type = candidate.get(
                "entity_type"
            )

            if not candidate_value:
                continue

            if (
                candidate_entity_type
                == entity_type
                and str(candidate_value).strip().lower()
                == str(value).strip().lower()
            ):
                continue

            result = self.compare_entities(
                source_type=entity_type,
                source_value=value,
                target_type=candidate_entity_type,
                target_value=str(
                    candidate_value
                ),
            )

            if result.score < minimum_score:
                continue

            results.append(
                result
            )

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return results[:limit]

    # ========================================================
    # SHARED NEIGHBORS
    # ========================================================

    def shared_neighbors(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Return the entities shared by two graph neighborhoods.
        """

        source_neighbors = (
            self.queries.get_neighbors(
                entity_type=source_type,
                value=source_value,
                depth=depth,
            )
        )

        target_neighbors = (
            self.queries.get_neighbors(
                entity_type=target_type,
                value=target_value,
                depth=depth,
            )
        )

        target_keys = {
            self._entity_key(
                entity
            )
            for entity in target_neighbors
        }

        shared: list[
            dict[str, Any]
        ] = []

        for entity in source_neighbors:

            if (
                self._entity_key(entity)
                in target_keys
            ):
                shared.append(
                    entity
                )

        return shared

    # ========================================================
    # SAME TYPE SIMILARITY
    # ========================================================

    def compare_same_type(
        self,
        entity_type: str,
        first_value: str,
        second_value: str,
        depth: int = 1,
    ) -> SimilarityResult:
        """
        Compare two entities of the same type.
        """

        return self.compare_entities(
            source_type=entity_type,
            source_value=first_value,
            target_type=entity_type,
            target_value=second_value,
            depth=depth,
        )

    # ========================================================
    # CANDIDATE SEARCH
    # ========================================================

    def _candidate_entities(
        self,
        entity_type: str,
        value: str,
        candidate_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Retrieve possible comparison candidates.
        """

        if candidate_type:

            query = """
            MATCH (n:Entity)

            WHERE n.entity_type = $candidate_type
              AND NOT (
                  n.entity_type = $entity_type
                  AND n.normalized_value =
                      $normalized_value
              )

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value

            LIMIT $limit
            """

            parameters = {
                "candidate_type": candidate_type,
                "entity_type": entity_type,
                "normalized_value": value.lower(),
                "limit": limit,
            }

        else:

            query = """
            MATCH (n:Entity)

            WHERE NOT (
                n.entity_type = $entity_type
                AND n.normalized_value =
                    $normalized_value
            )

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value

            LIMIT $limit
            """

            parameters = {
                "entity_type": entity_type,
                "normalized_value": value.lower(),
                "limit": limit,
            }

        records = self.client.execute_read(
            query,
            parameters,
        )

        return [
            dict(record)
            for record in records
        ]

    # ========================================================
    # ENTITY KEY
    # ========================================================

    @staticmethod
    def _entity_key(
        entity: dict[str, Any],
    ) -> str:
        """
        Create a normalized key for an entity.
        """

        entity_type = entity.get(
            "entity_type",
            "",
        )

        value = entity.get(
            "value",
            "",
        )

        return (
            f"{entity_type}:"
            f"{str(value).strip().lower()}"
        )

    # ========================================================
    # PARSE KEYS
    # ========================================================

    @staticmethod
    def _parse_entity_keys(
        keys: set[str],
    ) -> list[dict[str, Any]]:
        """
        Convert normalized entity keys into dictionaries.
        """

        entities: list[
            dict[str, Any]
        ] = []

        for key in sorted(keys):

            if ":" not in key:
                continue

            entity_type, value = key.split(
                ":",
                1,
            )

            entities.append(
                {
                    "entity_type": entity_type,
                    "value": value,
                }
            )

        return entities

    # ========================================================
    # EXPLANATION
    # ========================================================

    @staticmethod
    def _build_explanation(
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        score: float,
        shared_count: int,
    ) -> str:
        """
        Build a human-readable explanation.
        """

        if shared_count == 0:

            return (
                f"{source_type} '{source_value}' "
                f"and {target_type} '{target_value}' "
                "have no shared graph neighbors "
                "at the selected traversal depth."
            )

        if score >= 0.75:
            level = "high"

        elif score >= 0.50:
            level = "moderate"

        elif score >= 0.25:
            level = "limited"

        else:
            level = "low"

        return (
            f"{source_type} '{source_value}' "
            f"and {target_type} '{target_value}' "
            f"show {level} structural similarity "
            f"with {shared_count} shared graph "
            "neighbor(s)."
        )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def compare_entities(
    client: Neo4jClient,
    source_type: str,
    source_value: str,
    target_type: str,
    target_value: str,
) -> SimilarityResult:
    """
    Convenience wrapper for entity comparison.
    """

    engine = SimilarityEngine(
        client
    )

    return engine.compare_entities(
        source_type=source_type,
        source_value=source_value,
        target_type=target_type,
        target_value=target_value,
    )


def find_similar_entities(
    client: Neo4jClient,
    entity_type: str,
    value: str,
    limit: int = 20,
) -> list[SimilarityResult]:
    """
    Convenience wrapper for similarity search.
    """

    engine = SimilarityEngine(
        client
    )

    return engine.find_similar_entities(
        entity_type=entity_type,
        value=value,
        limit=limit,
    )
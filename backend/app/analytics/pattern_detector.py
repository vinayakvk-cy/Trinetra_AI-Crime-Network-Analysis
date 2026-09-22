"""
TRINETRA Pattern Detector
=========================

Detects potentially relevant patterns in investigation data.

Responsibilities
----------------
- Detect highly connected entities
- Detect shared entities
- Detect repeated relationships
- Detect relationship concentration
- Detect short graph paths
- Produce explainable pattern observations

This module does NOT:
- Determine guilt
- Make legal conclusions
- Assign final risk scores
- Create or modify Neo4j data
- Replace human investigation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.analytics.graph_algorithms import GraphAnalytics
from app.graph.graph_queries import GraphQueries
from app.graph.neo4j_client import Neo4jClient


# ============================================================
# PATTERN RESULT
# ============================================================


@dataclass
class PatternResult:
    """
    Represents one detected graph pattern.
    """

    pattern_type: str

    title: str

    description: str

    confidence: float = 0.0

    severity: str = "informational"

    entities: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the pattern result into a dictionary.
        """

        return {
            "pattern_type": self.pattern_type,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "severity": self.severity,
            "entities": self.entities,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


# ============================================================
# PATTERN DETECTOR
# ============================================================


class PatternDetector:
    """
    Detects structural patterns in the investigation graph.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:

        self.client = client

        self.analytics = GraphAnalytics(
            client
        )

        self.queries = GraphQueries(
            client
        )

    # ========================================================
    # HIGH CONNECTIVITY
    # ========================================================

    def detect_high_connectivity(
        self,
        limit: int = 20,
        minimum_degree: int = 5,
    ) -> list[PatternResult]:
        """
        Detect entities with unusually high connectivity.
        """

        entities = (
            self.analytics.top_connected_entities(
                limit=limit
            )
        )

        results: list[PatternResult] = []

        for entity in entities:

            degree = int(
                entity.get(
                    "degree",
                    0,
                )
                or 0
            )

            if degree < minimum_degree:
                continue

            entity_type = entity.get(
                "entity_type"
            )

            value = entity.get(
                "value"
            )

            results.append(
                PatternResult(
                    pattern_type=(
                        "HIGH_CONNECTIVITY"
                    ),
                    title=(
                        "Highly connected entity"
                    ),
                    description=(
                        f"{entity_type} "
                        f"'{value}' has "
                        f"{degree} direct "
                        "graph connections."
                    ),
                    confidence=0.90,
                    severity="notable",
                    entities=[
                        {
                            "type": entity_type,
                            "value": value,
                            "node_id": entity.get(
                                "node_id"
                            ),
                        }
                    ],
                    evidence=[
                        {
                            "metric": "degree",
                            "value": degree,
                        }
                    ],
                )
            )

        return results

    # ========================================================
    # SHARED ENTITY
    # ========================================================

    def detect_shared_entity(
        self,
        entity_type: str,
        entity_value: str,
        minimum_people: int = 2,
    ) -> PatternResult | None:
        """
        Detect an entity shared by multiple people.

        Example:
            multiple people connected to the same phone,
            vehicle, device, or location.
        """

        analysis = (
            self.analytics.shared_entity_analysis(
                entity_type=entity_type,
                value=entity_value,
            )
        )

        people = analysis.get(
            "people",
            []
        )

        if len(people) < minimum_people:
            return None

        return PatternResult(
            pattern_type="SHARED_ENTITY",
            title="Shared entity detected",
            description=(
                f"{len(people)} people are "
                f"connected to the same "
                f"{entity_type}: "
                f"'{entity_value}'."
            ),
            confidence=0.95,
            severity="notable",
            entities=[
                {
                    "type": entity_type,
                    "value": entity_value,
                }
            ]
            + [
                {
                    "type": "PERSON",
                    "value": person.get(
                        "person"
                    ),
                    "node_id": person.get(
                        "person_id"
                    ),
                }
                for person in people
            ],
            evidence=people,
            metadata={
                "person_count": len(
                    people
                )
            },
        )

    # ========================================================
    # RELATIONSHIP DIVERSITY
    # ========================================================

    def detect_relationship_diversity(
        self,
        entity_type: str,
        entity_value: str,
        minimum_types: int = 3,
    ) -> PatternResult | None:
        """
        Detect entities connected through several different
        relationship types.
        """

        diversity = (
            self.analytics.relationship_diversity(
                entity_type=entity_type,
                value=entity_value,
            )
        )

        type_count = diversity.get(
            "relationship_types",
            0,
        )

        if type_count < minimum_types:
            return None

        relationship_types = diversity.get(
            "types",
            []
        )

        return PatternResult(
            pattern_type=(
                "RELATIONSHIP_DIVERSITY"
            ),
            title=(
                "Multiple relationship types"
            ),
            description=(
                f"{entity_type} "
                f"'{entity_value}' is "
                f"connected through "
                f"{type_count} different "
                "relationship types."
            ),
            confidence=0.85,
            severity="informational",
            entities=[
                {
                    "type": entity_type,
                    "value": entity_value,
                }
            ],
            evidence=[
                {
                    "relationship_types": (
                        relationship_types
                    )
                }
            ],
            metadata={
                "relationship_type_count": (
                    type_count
                )
            },
        )

    # ========================================================
    # BRIDGE ENTITY
    # ========================================================

    def detect_bridge_entities(
        self,
        limit: int = 20,
    ) -> list[PatternResult]:
        """
        Detect entities connecting diverse entity types.
        """

        bridges = (
            self.analytics.bridge_analysis(
                limit=limit
            )
        )

        results: list[PatternResult] = []

        for bridge in bridges:

            neighbor_types = int(
                bridge.get(
                    "neighbor_type_count",
                    0,
                )
                or 0
            )

            if neighbor_types < 2:
                continue

            entity_type = bridge.get(
                "entity_type"
            )

            value = bridge.get(
                "value"
            )

            results.append(
                PatternResult(
                    pattern_type="BRIDGE_ENTITY",
                    title=(
                        "Cross-domain bridge entity"
                    ),
                    description=(
                        f"{entity_type} "
                        f"'{value}' connects "
                        f"{neighbor_types} "
                        "different entity types."
                    ),
                    confidence=0.80,
                    severity="notable",
                    entities=[
                        {
                            "type": entity_type,
                            "value": value,
                            "node_id": bridge.get(
                                "node_id"
                            ),
                        }
                    ],
                    evidence=[
                        {
                            "neighbor_count": (
                                bridge.get(
                                    "neighbor_count",
                                    0,
                                )
                            ),
                            "neighbor_type_count": (
                                neighbor_types
                            ),
                        }
                    ],
                )
            )

        return results

    # ========================================================
    # SHORT PATH
    # ========================================================

    def detect_short_path(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        maximum_distance: int = 2,
    ) -> PatternResult | None:
        """
        Detect a short graph path between two entities.
        """

        path = self.analytics.path_analysis(
            source_type=source_type,
            source_value=source_value,
            target_type=target_type,
            target_value=target_value,
            max_depth=maximum_distance,
        )

        if not path:
            return None

        distance = path.get(
            "distance"
        )

        if distance is None:
            return None

        if distance > maximum_distance:
            return None

        return PatternResult(
            pattern_type="SHORT_GRAPH_PATH",
            title="Short graph path detected",
            description=(
                f"A graph path of length "
                f"{distance} connects "
                f"{source_type} '{source_value}' "
                f"and {target_type} "
                f"'{target_value}'."
            ),
            confidence=0.95,
            severity="informational",
            entities=[
                {
                    "type": source_type,
                    "value": source_value,
                },
                {
                    "type": target_type,
                    "value": target_value,
                },
            ],
            evidence=[
                {
                    "distance": distance,
                    "nodes": path.get(
                        "nodes",
                        [],
                    ),
                    "relationships": path.get(
                        "relationships",
                        [],
                    ),
                }
            ],
        )

    # ========================================================
    # PERSON CONNECTION PATTERNS
    # ========================================================

    def detect_person_patterns(
        self,
        person_value: str,
    ) -> list[PatternResult]:
        """
        Detect basic graph patterns around a person.
        """

        results: list[
            PatternResult
        ] = []

        profile = (
            self.analytics.analyze_entity(
                entity_type="PERSON",
                value=person_value,
            )
        )

        if profile is None:
            return results

        if profile.total_degree >= 5:

            results.append(
                PatternResult(
                    pattern_type=(
                        "PERSON_HIGH_CONNECTIVITY"
                    ),
                    title=(
                        "Highly connected person node"
                    ),
                    description=(
                        f"PERSON "
                        f"'{person_value}' "
                        f"has "
                        f"{profile.total_degree} "
                        "direct graph "
                        "connections."
                    ),
                    confidence=0.90,
                    severity="notable",
                    entities=[
                        {
                            "type": "PERSON",
                            "value": person_value,
                        }
                    ],
                    evidence=[
                        {
                            "total_degree": (
                                profile.total_degree
                            ),
                            "neighbor_count": (
                                profile.neighbor_count
                            ),
                        }
                    ],
                )
            )

        diversity = (
            self.analytics.relationship_diversity(
                entity_type="PERSON",
                value=person_value,
            )
        )

        if diversity.get(
            "relationship_types",
            0,
        ) >= 3:

            results.append(
                PatternResult(
                    pattern_type=(
                        "PERSON_MULTI_RELATION"
                    ),
                    title=(
                        "Person has diverse "
                        "relationship connections"
                    ),
                    description=(
                        f"PERSON "
                        f"'{person_value}' "
                        "is connected through "
                        f"{diversity['relationship_types']} "
                        "relationship types."
                    ),
                    confidence=0.85,
                    severity="informational",
                    entities=[
                        {
                            "type": "PERSON",
                            "value": person_value,
                        }
                    ],
                    evidence=[
                        {
                            "relationship_types": (
                                diversity.get(
                                    "types",
                                    [],
                                )
                            )
                        }
                    ],
                )
            )

        return results

    # ========================================================
    # CASE PATTERNS
    # ========================================================

    def detect_case_patterns(
        self,
        case_value: str,
    ) -> list[PatternResult]:
        """
        Analyze the immediate graph around a case.
        """

        results: list[
            PatternResult
        ] = []

        entities = (
            self.queries.get_case_entities(
                case_value=case_value
            )
        )

        if not entities:
            return results

        entity_type_counts: dict[
            str,
            int,
        ] = {}

        for entity in entities:

            entity_type = entity.get(
                "entity_type"
            )

            if not entity_type:
                continue

            entity_type_counts[
                entity_type
            ] = (
                entity_type_counts.get(
                    entity_type,
                    0,
                )
                + 1
            )

        results.append(
            PatternResult(
                pattern_type="CASE_GRAPH_PROFILE",
                title="Case graph profile",
                description=(
                    f"Case '{case_value}' "
                    f"has {len(entities)} "
                    "directly connected "
                    "entities."
                ),
                confidence=1.0,
                severity="informational",
                entities=entities,
                evidence=[
                    {
                        "entity_type_distribution": (
                            entity_type_counts
                        )
                    }
                ],
                metadata={
                    "connected_entity_count": (
                        len(entities)
                    )
                },
            )
        )

        return results

    # ========================================================
    # RUN ALL PATTERNS
    # ========================================================

    def detect_all(
        self,
        limit: int = 20,
    ) -> list[PatternResult]:
        """
        Run the general graph pattern detectors.
        """

        results: list[
            PatternResult
        ] = []

        results.extend(
            self.detect_high_connectivity(
                limit=limit
            )
        )

        results.extend(
            self.detect_bridge_entities(
                limit=limit
            )
        )

        return results

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @staticmethod
    def serialize(
        patterns: list[PatternResult],
    ) -> list[dict[str, Any]]:
        """
        Convert pattern objects to API-friendly dictionaries.
        """

        return [
            pattern.to_dict()
            for pattern in patterns
        ]


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def detect_person_patterns(
    client: Neo4jClient,
    person_value: str,
) -> list[PatternResult]:
    """
    Convenience wrapper for person pattern detection.
    """

    detector = PatternDetector(client)

    return detector.detect_person_patterns(
        person_value=person_value
    )


def detect_case_patterns(
    client: Neo4jClient,
    case_value: str,
) -> list[PatternResult]:
    """
    Convenience wrapper for case pattern detection.
    """

    detector = PatternDetector(client)

    return detector.detect_case_patterns(
        case_value=case_value
    )

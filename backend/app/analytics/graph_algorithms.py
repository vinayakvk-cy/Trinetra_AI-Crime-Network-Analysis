"""
TRINETRA Graph Analytics
========================

Higher-level analytics built on top of the graph layer.

Responsibilities
----------------
- Analyze entity connectivity
- Analyze local graph structure
- Identify highly connected entities
- Analyze relationship distributions
- Produce explainable graph metrics
- Provide investigation-oriented graph summaries

This module does NOT:
- Build Neo4j nodes
- Create relationships
- Extract entities
- Determine guilt
- Make legal conclusions
- Replace the risk engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.graph.graph_algorithms import GraphAlgorithms
from app.graph.graph_queries import GraphQueries
from app.graph.neo4j_client import Neo4jClient


# ============================================================
# GRAPH ANALYTIC RESULT
# ============================================================


@dataclass
class GraphMetric:
    """
    One graph-derived analytical metric.
    """

    metric_name: str

    value: float | int

    description: str

    entity_type: str | None = None

    entity_value: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metric to dictionary.
        """

        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "description": self.description,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "metadata": self.metadata,
        }


# ============================================================
# ENTITY GRAPH PROFILE
# ============================================================


@dataclass
class EntityGraphProfile:
    """
    Structural profile of one entity in the graph.
    """

    entity_type: str

    entity_value: str

    total_degree: int

    incoming_degree: int

    outgoing_degree: int

    neighbor_count: int = 0

    relationship_count: int = 0

    metrics: list[GraphMetric] = field(
        default_factory=list
    )

    connections: list[dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert profile to dictionary.
        """

        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "total_degree": self.total_degree,
            "incoming_degree": self.incoming_degree,
            "outgoing_degree": self.outgoing_degree,
            "neighbor_count": self.neighbor_count,
            "relationship_count": self.relationship_count,
            "metrics": [
                metric.to_dict()
                for metric in self.metrics
            ],
            "connections": self.connections,
        }


# ============================================================
# GRAPH ANALYTICS
# ============================================================


class GraphAnalytics:
    """
    Higher-level analytics service for the investigation graph.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:

        self.client = client

        self.algorithms = GraphAlgorithms(
            client
        )

        self.queries = GraphQueries(
            client
        )

    # ========================================================
    # ENTITY PROFILE
    # ========================================================

    def analyze_entity(
        self,
        entity_type: str,
        value: str,
    ) -> EntityGraphProfile | None:
        """
        Build a structural graph profile for an entity.
        """

        degree = self.algorithms.node_degree(
            entity_type=entity_type,
            value=value,
        )

        if not degree:
            return None

        connections = (
            self.queries.get_relationships(
                entity_type=entity_type,
                value=value,
            )
        )

        neighbors = (
            self.queries.get_neighbors(
                entity_type=entity_type,
                value=value,
                depth=1,
            )
        )

        total_degree = int(
            degree.get(
                "total_degree",
                0,
            )
            or 0
        )

        incoming_degree = int(
            degree.get(
                "incoming_degree",
                0,
            )
            or 0
        )

        outgoing_degree = int(
            degree.get(
                "outgoing_degree",
                0,
            )
            or 0
        )

        metrics = [
            GraphMetric(
                metric_name="total_degree",
                value=total_degree,
                description=(
                    "Total number of direct graph "
                    "connections."
                ),
                entity_type=entity_type,
                entity_value=value,
            ),
            GraphMetric(
                metric_name="incoming_degree",
                value=incoming_degree,
                description=(
                    "Number of relationships directed "
                    "toward this entity."
                ),
                entity_type=entity_type,
                entity_value=value,
            ),
            GraphMetric(
                metric_name="outgoing_degree",
                value=outgoing_degree,
                description=(
                    "Number of relationships directed "
                    "from this entity."
                ),
                entity_type=entity_type,
                entity_value=value,
            ),
            GraphMetric(
                metric_name="neighbor_count",
                value=len(neighbors),
                description=(
                    "Number of distinct entities "
                    "directly connected."
                ),
                entity_type=entity_type,
                entity_value=value,
            ),
        ]

        return EntityGraphProfile(
            entity_type=entity_type,
            entity_value=value,
            total_degree=total_degree,
            incoming_degree=incoming_degree,
            outgoing_degree=outgoing_degree,
            neighbor_count=len(neighbors),
            relationship_count=len(connections),
            metrics=metrics,
            connections=connections,
        )

    # ========================================================
    # TOP CONNECTED
    # ========================================================

    def top_connected_entities(
        self,
        limit: int = 20,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return the most connected entities.
        """

        return (
            self.algorithms.most_connected_entities(
                limit=limit,
                entity_type=entity_type,
            )
        )

    # ========================================================
    # CONNECTION SCORE
    # ========================================================

    def connection_score(
        self,
        entity_type: str,
        value: str,
    ) -> float:
        """
        Calculate a normalized connectivity score.

        The score is based on degree relative to the highest
        degree currently present in the graph.

        This is NOT a risk score.
        """

        profile = self.analyze_entity(
            entity_type=entity_type,
            value=value,
        )

        if profile is None:
            return 0.0

        highest = (
            self.algorithms.most_connected_entities(
                limit=1
            )
        )

        if not highest:
            return 0.0

        maximum_degree = float(
            highest[0].get(
                "degree",
                0,
            )
            or 0
        )

        if maximum_degree <= 0:
            return 0.0

        score = (
            profile.total_degree
            / maximum_degree
        )

        return round(
            min(1.0, score),
            4,
        )

    # ========================================================
    # RELATIONSHIP DIVERSITY
    # ========================================================

    def relationship_diversity(
        self,
        entity_type: str,
        value: str,
    ) -> dict[str, Any]:
        """
        Calculate the diversity of relationship types
        connected to an entity.
        """

        relationships = (
            self.queries.get_relationships(
                entity_type=entity_type,
                value=value,
            )
        )

        if not relationships:
            return {
                "relationship_types": 0,
                "relationships": 0,
                "types": [],
            }

        relationship_types = sorted(
            {
                relation.get(
                    "relationship_type"
                )
                for relation in relationships
                if relation.get(
                    "relationship_type"
                )
            }
        )

        return {
            "relationship_types": len(
                relationship_types
            ),
            "relationships": len(
                relationships
            ),
            "types": relationship_types,
        }

    # ========================================================
    # NEIGHBORHOOD ANALYSIS
    # ========================================================

    def analyze_neighborhood(
        self,
        entity_type: str,
        value: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """
        Analyze the local neighborhood around an entity.
        """

        neighbors = (
            self.queries.get_neighbors(
                entity_type=entity_type,
                value=value,
                depth=depth,
            )
        )

        density = (
            self.algorithms.neighborhood_density(
                entity_type=entity_type,
                value=value,
                depth=min(depth, 3),
            )
        )

        entity_type_counts: dict[
            str,
            int,
        ] = {}

        for neighbor in neighbors:

            neighbor_type = neighbor.get(
                "entity_type"
            )

            if not neighbor_type:
                continue

            entity_type_counts[
                neighbor_type
            ] = (
                entity_type_counts.get(
                    neighbor_type,
                    0,
                )
                + 1
            )

        return {
            "entity_type": entity_type,
            "entity_value": value,
            "depth": depth,
            "neighbor_count": len(
                neighbors
            ),
            "entity_type_distribution": (
                entity_type_counts
            ),
            "density": density.get(
                "density",
                0.0,
            ),
            "neighbors": neighbors,
        }

    # ========================================================
    # SHARED ENTITY ANALYSIS
    # ========================================================

    def shared_entity_analysis(
        self,
        entity_type: str,
        value: str,
    ) -> dict[str, Any]:
        """
        Analyze people connected to a shared entity.

        Example:
            PHONE -> multiple people
            DEVICE -> multiple people
            VEHICLE -> multiple people
        """

        people = (
            self.queries.find_people_sharing_entity(
                entity_type=entity_type,
                entity_value=value,
            )
        )

        return {
            "entity_type": entity_type,
            "entity_value": value,
            "person_count": len(people),
            "people": people,
        }

    # ========================================================
    # GRAPH OVERVIEW
    # ========================================================

    def overview(
        self,
    ) -> dict[str, Any]:
        """
        Return a high-level graph overview.
        """

        statistics = (
            self.algorithms.relationship_distribution()
        )

        entity_distribution = (
            self.algorithms.entity_distribution()
        )

        return {
            "entity_distribution": (
                entity_distribution
            ),
            "relationship_distribution": (
                statistics
            ),
        }

    # ========================================================
    # STRUCTURAL OUTLIERS
    # ========================================================

    def structural_outliers(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Identify entities that are unusually connected
        compared with the rest of the graph.

        This is a structural observation and should not be
        interpreted as evidence of wrongdoing by itself.
        """

        top_entities = (
            self.algorithms.most_connected_entities(
                limit=limit
            )
        )

        return [
            {
                **entity,
                "observation": (
                    "High graph connectivity"
                ),
            }
            for entity in top_entities
            if (
                entity.get("degree", 0)
                and entity["degree"] > 0
            )
        ]

    # ========================================================
    # BRIDGE ANALYSIS
    # ========================================================

    def bridge_analysis(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Return entities that connect diverse entity types.
        """

        return (
            self.algorithms.bridge_entities(
                limit=limit
            )
        )

    # ========================================================
    # PATH ANALYSIS
    # ========================================================

    def path_analysis(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        max_depth: int = 10,
    ) -> dict[str, Any] | None:
        """
        Analyze the shortest structural path between
        two entities.
        """

        path = (
            self.algorithms.shortest_path(
                source_type=source_type,
                source_value=source_value,
                target_type=target_type,
                target_value=target_value,
                max_depth=max_depth,
            )
        )

        if path is None:
            return None

        distance = path.get(
            "distance"
        )

        return {
            "source": {
                "type": source_type,
                "value": source_value,
            },
            "target": {
                "type": target_type,
                "value": target_value,
            },
            "distance": distance,
            "nodes": path.get(
                "nodes",
                [],
            ),
            "relationships": path.get(
                "relationships",
                [],
            ),
            "connected": True,
        }


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def analyze_entity(
    client: Neo4jClient,
    entity_type: str,
    value: str,
) -> EntityGraphProfile | None:
    """
    Convenience wrapper for entity analysis.
    """

    analytics = GraphAnalytics(client)

    return analytics.analyze_entity(
        entity_type=entity_type,
        value=value,
    )


def analyze_path(
    client: Neo4jClient,
    source_type: str,
    source_value: str,
    target_type: str,
    target_value: str,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for path analysis.
    """

    analytics = GraphAnalytics(client)

    return analytics.path_analysis(
        source_type=source_type,
        source_value=source_value,
        target_type=target_type,
        target_value=target_value,
    )
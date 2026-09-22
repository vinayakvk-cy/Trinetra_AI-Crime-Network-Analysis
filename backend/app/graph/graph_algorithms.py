"""
TRINETRA Graph Algorithms
=========================

Graph-level analytical operations.

Responsibilities
----------------
- Calculate node degree
- Find shortest paths
- Calculate basic centrality
- Find highly connected entities
- Detect connected components
- Provide graph-level structural information

This module does NOT:
- Build graph nodes
- Extract entities
- Extract relationships
- Assign criminal guilt
- Make legal conclusions
- Replace the analytics/risk engine
"""

from __future__ import annotations

from typing import Any

from app.graph.neo4j_client import Neo4jClient


class GraphAlgorithms:
    """
    Graph algorithms operating on the Neo4j investigation graph.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:
        self.client = client

    # ========================================================
    # NODE DEGREE
    # ========================================================

    def node_degree(
        self,
        entity_type: str,
        value: str,
    ) -> dict[str, Any]:
        """
        Calculate the number of incoming and outgoing
        relationships for an entity.
        """

        query = """
        MATCH (n:Entity {
            entity_type: $entity_type,
            normalized_value: $normalized_value
        })

        RETURN
            elementId(n) AS node_id,
            n.entity_type AS entity_type,
            n.value AS value,
            size((n)-->) AS outgoing_degree,
            size((n)<--) AS incoming_degree,
            size((n)--()) AS total_degree
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type,
                "normalized_value": value.lower(),
            },
        )

        if not records:
            return {}

        return dict(records[0])

    # ========================================================
    # TOP CONNECTED ENTITIES
    # ========================================================

    def most_connected_entities(
        self,
        limit: int = 20,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return entities with the highest number of
        relationships.

        This is a structural graph measure, not a risk score.
        """

        limit = self._validate_limit(limit)

        if entity_type:

            query = """
            MATCH (n:Entity)
            WHERE n.entity_type = $entity_type

            OPTIONAL MATCH (n)--(connected)

            WITH
                n,
                count(DISTINCT connected) AS degree

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value,
                degree

            ORDER BY degree DESC, n.value
            LIMIT $limit
            """

            parameters = {
                "entity_type": entity_type,
                "limit": limit,
            }

        else:

            query = """
            MATCH (n:Entity)

            OPTIONAL MATCH (n)--(connected)

            WITH
                n,
                count(DISTINCT connected) AS degree

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value,
                degree

            ORDER BY degree DESC, n.value
            LIMIT $limit
            """

            parameters = {
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
    # SHORTEST PATH
    # ========================================================

    def shortest_path(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        max_depth: int = 10,
    ) -> dict[str, Any] | None:
        """
        Find the shortest path between two entities.
        """

        max_depth = self._validate_depth(
            max_depth
        )

        query = f"""
        MATCH (
            source:Entity {{
                entity_type: $source_type,
                normalized_value: $source_value
            }}
        )

        MATCH (
            target:Entity {{
                entity_type: $target_type,
                normalized_value: $target_value
            }}
        )

        MATCH path =
            shortestPath(
                (source)-[*..{max_depth}]-(target)
            )

        RETURN
            [
                node IN nodes(path) |
                {{
                    id: elementId(node),
                    type: node.entity_type,
                    value: node.value
                }}
            ] AS nodes,

            [
                relationship IN relationships(path) |
                {{
                    id: elementId(relationship),
                    type: type(relationship),
                    source:
                        elementId(
                            startNode(relationship)
                        ),
                    target:
                        elementId(
                            endNode(relationship)
                        ),
                    confidence:
                        relationship.confidence
                }}
            ] AS relationships,

            length(path) AS distance
        """

        records = self.client.execute_read(
            query,
            {
                "source_type": source_type,
                "source_value": source_value.lower(),
                "target_type": target_type,
                "target_value": target_value.lower(),
            },
        )

        if not records:
            return None

        return dict(records[0])

    # ========================================================
    # BETWEENNESS-LIKE CONNECTIVITY
    # ========================================================

    def bridge_entities(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Find entities that connect otherwise distinct
        neighborhoods.

        This implementation uses a local approximation based
        on the number of distinct neighboring entity types.

        A full betweenness-centrality implementation can be
        introduced later if required.
        """

        limit = self._validate_limit(limit)

        query = """
        MATCH (n:Entity)

        OPTIONAL MATCH (n)--(neighbor:Entity)

        WITH
            n,
            count(DISTINCT neighbor) AS neighbor_count,
            count(
                DISTINCT neighbor.entity_type
            ) AS neighbor_type_count

        RETURN
            elementId(n) AS node_id,
            n.entity_type AS entity_type,
            n.value AS value,
            neighbor_count,
            neighbor_type_count

        ORDER BY
            neighbor_type_count DESC,
            neighbor_count DESC

        LIMIT $limit
        """

        records = self.client.execute_read(
            query,
            {
                "limit": limit,
            },
        )

        return [
            dict(record)
            for record in records
        ]

    # ========================================================
    # NEIGHBORHOOD DENSITY
    # ========================================================

    def neighborhood_density(
        self,
        entity_type: str,
        value: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        """
        Estimate the density of an entity's local neighborhood.

        Density is calculated as:

            existing relationships /
            possible relationships

        This is a local structural measure.
        """

        depth = self._validate_depth(
            depth,
            maximum=3,
        )

        query = f"""
        MATCH (
            source:Entity {{
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }}
        )

        MATCH path =
            (source)-[*1..{depth}]-(neighbor:Entity)

        WITH
            source,
            collect(DISTINCT neighbor) AS neighbors

        UNWIND neighbors AS n

        OPTIONAL MATCH (n)--(m:Entity)

        WITH
            source,
            neighbors,
            count(DISTINCT m) AS edge_count

        WITH
            source,
            size(neighbors) AS node_count,
            edge_count

        RETURN
            elementId(source) AS node_id,
            source.value AS value,
            node_count,
            edge_count,
            CASE
                WHEN node_count <= 1
                THEN 0.0
                ELSE
                    toFloat(edge_count)
                    /
                    toFloat(
                        node_count * (node_count - 1)
                    )
            END AS density
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type,
                "normalized_value": value.lower(),
            },
        )

        if not records:
            return {}

        return dict(records[0])

    # ========================================================
    # CONNECTED COMPONENT
    # ========================================================

    def connected_component(
        self,
        entity_type: str,
        value: str,
        max_depth: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Return entities reachable from a starting entity.

        The traversal is bounded to avoid unrestricted graph
        expansion.
        """

        max_depth = self._validate_depth(
            max_depth
        )

        query = f"""
        MATCH (
            source:Entity {{
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }}
        )

        MATCH path =
            (source)-[*0..{max_depth}]-(target:Entity)

        RETURN DISTINCT
            elementId(target) AS node_id,
            target.entity_type AS entity_type,
            target.value AS value,
            min(length(path)) AS distance

        ORDER BY distance, target.entity_type, target.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type,
                "normalized_value": value.lower(),
            },
        )

        return [
            dict(record)
            for record in records
        ]

    # ========================================================
    # RELATIONSHIP DISTRIBUTION
    # ========================================================

    def relationship_distribution(
        self,
    ) -> list[dict[str, Any]]:
        """
        Count relationships by relationship type.
        """

        query = """
        MATCH ()-[r]->()

        RETURN
            type(r) AS relationship_type,
            count(r) AS count

        ORDER BY count DESC
        """

        records = self.client.execute_read(
            query
        )

        return [
            dict(record)
            for record in records
        ]

    # ========================================================
    # ENTITY DISTRIBUTION
    # ========================================================

    def entity_distribution(
        self,
    ) -> list[dict[str, Any]]:
        """
        Count nodes by entity type.
        """

        query = """
        MATCH (n:Entity)

        RETURN
            n.entity_type AS entity_type,
            count(n) AS count

        ORDER BY count DESC
        """

        records = self.client.execute_read(
            query
        )

        return [
            dict(record)
            for record in records
        ]

    # ========================================================
    # LOCAL GRAPH SUMMARY
    # ========================================================

    def local_summary(
        self,
        entity_type: str,
        value: str,
    ) -> dict[str, Any]:
        """
        Return a compact structural summary for one entity.
        """

        degree = self.node_degree(
            entity_type,
            value,
        )

        if not degree:
            return {}

        return {
            "node_id": degree.get(
                "node_id"
            ),
            "entity_type": degree.get(
                "entity_type"
            ),
            "value": degree.get(
                "value"
            ),
            "incoming_degree": degree.get(
                "incoming_degree",
                0,
            ),
            "outgoing_degree": degree.get(
                "outgoing_degree",
                0,
            ),
            "total_degree": degree.get(
                "total_degree",
                0,
            ),
        }

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _validate_limit(
        limit: int,
        maximum: int = 100,
    ) -> int:
        """
        Validate result limits.
        """

        if not isinstance(limit, int):
            raise TypeError(
                "Limit must be an integer."
            )

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        if limit > maximum:
            raise ValueError(
                f"Limit cannot exceed {maximum}."
            )

        return limit

    @staticmethod
    def _validate_depth(
        depth: int,
        maximum: int = 10,
    ) -> int:
        """
        Validate traversal depth.
        """

        if not isinstance(depth, int):
            raise TypeError(
                "Depth must be an integer."
            )

        if depth < 1:
            raise ValueError(
                "Depth must be at least 1."
            )

        if depth > maximum:
            raise ValueError(
                f"Depth cannot exceed {maximum}."
            )

        return depth


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def get_node_degree(
    client: Neo4jClient,
    entity_type: str,
    value: str,
) -> dict[str, Any]:
    """
    Convenience wrapper for node degree.
    """

    algorithms = GraphAlgorithms(client)

    return algorithms.node_degree(
        entity_type=entity_type,
        value=value,
    )


def find_shortest_path(
    client: Neo4jClient,
    source_type: str,
    source_value: str,
    target_type: str,
    target_value: str,
    max_depth: int = 10,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for shortest path.
    """

    algorithms = GraphAlgorithms(client)

    return algorithms.shortest_path(
        source_type=source_type,
        source_value=source_value,
        target_type=target_type,
        target_value=target_value,
        max_depth=max_depth,
    )
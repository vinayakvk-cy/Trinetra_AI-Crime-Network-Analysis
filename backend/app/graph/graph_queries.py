"""
TRINETRA Graph Queries
======================

Read-only investigation queries for the Neo4j graph.

Responsibilities
----------------
- Find entities
- Find entity relationships
- Find connected entities
- Find paths between entities
- Find case-related entities
- Support graph analytics
- Return graph data for the API/analytics layers

This module does NOT:
- Create nodes
- Create relationships
- Modify graph data
- Determine guilt
- Assign risk scores
"""

from __future__ import annotations

from typing import Any

from neo4j import Record

from app.graph.neo4j_client import Neo4jClient


class GraphQueries:
    """
    Read-only query layer for the investigation graph.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:
        self.client = client

    # ========================================================
    # FIND ENTITY
    # ========================================================

    def find_entity(
        self,
        entity_type: str,
        value: str,
    ) -> list[dict[str, Any]]:
        """
        Find entities by type and normalized value.
        """

        query = """
        MATCH (
            n:Entity {
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }
        )

        RETURN
            elementId(n) AS node_id,
            n.entity_type AS entity_type,
            n.value AS value,
            n.normalized_value AS normalized_value,
            n.source_field AS source_field
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "normalized_value": value.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # SEARCH ENTITIES
    # ========================================================

    def search_entities(
        self,
        value: str,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search entities by value.

        Exact normalized matching is preferred here. More
        advanced fuzzy search can be added later.
        """

        if entity_type:
            query = """
            MATCH (n:Entity)
            WHERE
                n.entity_type = $entity_type
                AND (
                    toLower(coalesce(n.value, "")) CONTAINS
                    toLower($value)
                    OR
                    toLower(coalesce(n.normalized_value, "")) CONTAINS
                    toLower($value)
                )

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value,
                n.normalized_value AS normalized_value
            ORDER BY n.value
            """

            parameters = {
                "entity_type": entity_type.strip().lower(),
                "value": value,
            }

        else:
            query = """
            MATCH (n:Entity)
            WHERE
                toLower(coalesce(n.value, "")) CONTAINS
                toLower($value)
                OR
                toLower(coalesce(n.normalized_value, "")) CONTAINS
                toLower($value)

            RETURN
                elementId(n) AS node_id,
                n.entity_type AS entity_type,
                n.value AS value,
                n.normalized_value AS normalized_value
            ORDER BY n.entity_type, n.value
            """

            parameters = {
                "value": value,
            }

        records = self.client.execute_read(
            query,
            parameters,
        )

        return self._records_to_dicts(records)

    # ========================================================
    # ENTITY RELATIONSHIPS
    # ========================================================

    def get_relationships(
        self,
        entity_type: str,
        value: str,
    ) -> list[dict[str, Any]]:
        """
        Return all direct relationships for an entity.
        """

        query = """
        MATCH (
            source:Entity {
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }
        )-[r]-(target:Entity)

        RETURN
            elementId(source) AS source_id,
            source.entity_type AS source_type,
            source.value AS source_value,

            type(r) AS relationship_type,

            elementId(target) AS target_id,
            target.entity_type AS target_type,
            target.value AS target_value,

            r.confidence AS confidence,
            r.evidence_text AS evidence_text,
            r.source_field AS source_field
        ORDER BY target.entity_type, target.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "normalized_value": value.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # NEIGHBORS
    # ========================================================

    def get_neighbors(
        self,
        entity_type: str,
        value: str,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Return entities connected within a specified depth.
        """

        depth = self._validate_depth(depth)

        query = f"""
        MATCH (
            source:Entity {{
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }}
        )

        MATCH path =
            (source)-[*1..{depth}]-(target:Entity)

        WHERE source <> target

        RETURN DISTINCT
            elementId(target) AS node_id,
            target.entity_type AS entity_type,
            target.value AS value,
            target.normalized_value AS normalized_value,
            length(path) AS distance
        ORDER BY distance, target.entity_type, target.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "normalized_value": value.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # PATH BETWEEN ENTITIES
    # ========================================================

    def find_paths(
        self,
        source_type: str,
        source_value: str,
        target_type: str,
        target_value: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find the shortest path between two entities.
        """

        max_depth = self._validate_depth(
            max_depth,
            maximum=10,
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
                    type: type(relationship),
                    confidence: relationship.confidence
                }}
            ] AS relationships,

            length(path) AS distance
        """

        records = self.client.execute_read(
            query,
            {
                "source_type": source_type.strip().lower(),
                "source_value": source_value.lower(),
                "target_type": target_type.strip().lower(),
                "target_value": target_value.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # CASE ENTITIES
    # ========================================================

    def get_case_entities(
        self,
        case_value: str,
    ) -> list[dict[str, Any]]:
        """
        Return entities directly connected to a case.

        The graph schema expects a CASE node represented as:

            (:Entity {
                entity_type: "case",
                normalized_value: <case_value>
            })
        """

        query = """
        MATCH (
            case:Entity {
                entity_type: "case",
                normalized_value: $case_value
            }
        )

        MATCH (case)-[r]-(entity:Entity)

        RETURN
            elementId(entity) AS node_id,
            entity.entity_type AS entity_type,
            entity.value AS value,
            entity.normalized_value AS normalized_value,
            type(r) AS relationship_type,
            r.confidence AS confidence,
            r.evidence_text AS evidence_text
        ORDER BY entity.entity_type, entity.value
        """

        records = self.client.execute_read(
            query,
            {
                "case_value": case_value.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # ENTITY DEGREE
    # ========================================================

    def get_entity_degree(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return the number of direct relationships for an entity.

        entity_id is expected to be a Neo4j elementId().
        """

        query = """
        MATCH (entity:Entity)
        WHERE elementId(entity) = $entity_id

        OPTIONAL MATCH (entity)-[r]-()

        RETURN
            elementId(entity) AS entity_id,
            entity.entity_type AS entity_type,
            entity.value AS value,
            count(r) AS degree
        """

        records = self.client.execute_read(
            query,
            {
                "entity_id": entity_id,
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # CROSS-CASE ENTITIES
    # ========================================================

    def find_cross_case_entities(
        self,
        case_id: str,
    ) -> list[dict[str, Any]]:
        """
        Find entities associated with more than one CASE.

        If CASE nodes are not present in the graph, this safely
        returns an empty list.
        """

        query = """
        MATCH (
            entity:Entity
        )-[]-(case:Entity)

        WHERE
            case.entity_type = "case"
            AND case.normalized_value = $case_id

        WITH entity

        MATCH (
            entity
        )-[]-(other_case:Entity)

        WHERE other_case.entity_type = "case"

        WITH
            entity,
            collect(
                DISTINCT other_case.normalized_value
            ) AS case_ids

        WHERE size(case_ids) > 1

        RETURN
            elementId(entity) AS entity_id,
            entity.entity_type AS entity_type,
            entity.value AS entity_name,
            case_ids,
            size(case_ids) AS case_count

        ORDER BY case_count DESC
        """

        records = self.client.execute_read(
            query,
            {
                "case_id": case_id.lower(),
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # SHARED PHONES
    # ========================================================

    def find_shared_phones(
        self,
        case_id: str,
    ) -> list[dict[str, Any]]:
        """
        Find phone entities connected to multiple people.

        The case_id is retained for analytics compatibility.
        """

        query = """
        MATCH (phone:Entity)

        WHERE phone.entity_type = "PHONE"

        MATCH (person:Entity)-[r]-(phone)

        WHERE person.entity_type = "PERSON"

        WITH
            phone,
            collect(DISTINCT person) AS people

        WHERE size(people) > 1

        RETURN
            elementId(phone) AS phone_id,
            phone.value AS phone_number,
            phone.normalized_value AS normalized_value,
            [
                person IN people |
                elementId(person)
            ] AS entity_ids,
            [
                person IN people |
                person.value
            ] AS entity_names,
            size(people) AS entity_count

        ORDER BY entity_count DESC
        """

        records = self.client.execute_read(query)

        return self._records_to_dicts(records)

    # ========================================================
    # SHARED VEHICLES
    # ========================================================

    def find_shared_vehicles(
        self,
        case_id: str,
    ) -> list[dict[str, Any]]:
        """
        Find vehicle entities connected to multiple people.

        The case_id is retained for analytics compatibility.
        """

        query = """
        MATCH (vehicle:Entity)

        WHERE vehicle.entity_type = "VEHICLE"

        MATCH (person:Entity)-[r]-(vehicle)

        WHERE person.entity_type = "PERSON"

        WITH
            vehicle,
            collect(DISTINCT person) AS people

        WHERE size(people) > 1

        RETURN
            elementId(vehicle) AS vehicle_id,
            vehicle.value AS vehicle_identifier,
            vehicle.normalized_value AS normalized_value,
            [
                person IN people |
                elementId(person)
            ] AS entity_ids,
            [
                person IN people |
                person.value
            ] AS entity_names,
            size(people) AS entity_count

        ORDER BY entity_count DESC
        """

        records = self.client.execute_read(query)

        return self._records_to_dicts(records)

    # ========================================================
    # ENTITY COUNTS
    # ========================================================

    def get_entity_counts(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return counts of entities grouped by entity type.
        """

        query = """
        MATCH (entity:Entity)

        RETURN
            entity.entity_type AS entity_type,
            count(entity) AS count

        ORDER BY count DESC
        """

        records = self.client.execute_read(query)

        return self._records_to_dicts(records)

    # ========================================================
    # CASE GRAPH STATISTICS
    # ========================================================

    def get_case_graph_statistics(
        self,
        case_value: str,
    ) -> dict[str, int]:
        """
        Return live Neo4j node/relationship counts for one case.

        The CASE node itself is excluded from the entity count so
        the metric represents the investigation's connected
        intelligence entities.
        """

        query = """
        MATCH (
            case:Entity {
                entity_type: "case",
                normalized_value: $case_value
            }
        )

        OPTIONAL MATCH (case)-[r]-(entity:Entity)
        WHERE entity.entity_type <> "case"

        RETURN
            count(DISTINCT entity) AS node_count,
            count(r) AS relationship_count
        """

        records = self.client.execute_read(
            query,
            {
                "case_value": case_value.strip().lower(),
            },
        )

        if not records:
            return {
                "node_count": 0,
                "relationship_count": 0,
            }

        return {
            "node_count": int(records[0].get("node_count", 0) or 0),
            "relationship_count": int(
                records[0].get("relationship_count", 0) or 0
            ),
        }

    # ========================================================
    # PHONE NETWORK
    # ========================================================

    def get_phone_network(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return phone-related connections for an entity.

        Supports analytics without requiring a specific
        relationship type.
        """

        query = """
        MATCH (entity:Entity)
        WHERE elementId(entity) = $entity_id

        MATCH (entity)-[r]-(phone:Entity)

        WHERE phone.entity_type = "PHONE"

        RETURN
            elementId(entity) AS entity_id,
            entity.value AS entity_value,
            elementId(phone) AS phone_id,
            phone.value AS phone_number,
            type(r) AS relationship_type,
            r.confidence AS confidence

        ORDER BY phone.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_id": entity_id,
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # ENTITY LOCATIONS
    # ========================================================

    def get_entity_locations(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return location-related connections for an entity.
        """

        query = """
        MATCH (entity:Entity)
        WHERE elementId(entity) = $entity_id

        MATCH (entity)-[r]-(location:Entity)

        WHERE location.entity_type = "LOCATION"

        RETURN
            elementId(entity) AS entity_id,
            entity.value AS entity_value,
            elementId(location) AS location_id,
            location.value AS location,
            type(r) AS relationship_type,
            r.confidence AS confidence

        ORDER BY location.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_id": entity_id,
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # TRANSACTION NETWORK
    # ========================================================

    def get_transaction_network(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return transaction-related connections for an entity.
        """

        query = """
        MATCH (entity:Entity)
        WHERE elementId(entity) = $entity_id

        MATCH (entity)-[r]-(target:Entity)

        WHERE
            target.entity_type IN [
                "ORGANIZATION",
                "BANK",
                "ACCOUNT",
                "TRANSACTION"
            ]

        RETURN
            elementId(entity) AS entity_id,
            entity.value AS entity_value,
            elementId(target) AS target_id,
            target.entity_type AS target_type,
            target.value AS target_value,
            type(r) AS relationship_type,
            r.confidence AS confidence

        ORDER BY target.entity_type, target.value
        """

        records = self.client.execute_read(
            query,
            {
                "entity_id": entity_id,
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # FIND CONNECTION
    # ========================================================

    def find_connection(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find the shortest connection between two Neo4j nodes.
        """

        max_depth = self._validate_depth(
            max_depth,
            maximum=10,
        )

        query = f"""
        MATCH (source:Entity)
        WHERE elementId(source) = $source_id

        MATCH (target:Entity)
        WHERE elementId(target) = $target_id

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
                    confidence: relationship.confidence
                }}
            ] AS relationships,

            length(path) AS distance
        """

        records = self.client.execute_read(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
            },
        )

        return self._records_to_dicts(records)

    # ========================================================
    # GRAPH SUBSET
    # ========================================================

    def get_subgraph(
        self,
        entity_type: str,
        entity_value: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """
        Return a graph subset around an entity.
        """

        depth = self._validate_depth(depth)

        query = f"""
        MATCH (
            source:Entity {{
                entity_type: $entity_type,
                normalized_value: $normalized_value
            }}
        )

        MATCH path =
            (source)-[*0..{depth}]-(target:Entity)

        WITH collect(path) AS paths

        UNWIND paths AS path

        UNWIND nodes(path) AS node

        WITH
            collect(
                DISTINCT {{
                    id: elementId(node),
                    type: node.entity_type,
                    value: node.value
                }}
            ) AS nodes,
            paths

        UNWIND paths AS path

        UNWIND relationships(path) AS relationship

        WITH
            nodes,
            collect(
                DISTINCT {{
                    id: elementId(relationship),
                    type: type(relationship),
                    source: elementId(
                        startNode(relationship)
                    ),
                    target: elementId(
                        endNode(relationship)
                    ),
                    confidence: relationship.confidence
                }}
            ) AS relationships

        RETURN nodes, relationships
        """

        records = self.client.execute_read(
            query,
            {
                "entity_type": entity_type.strip().lower(),
                "normalized_value": entity_value.lower(),
            },
        )

        if not records:
            return {
                "nodes": [],
                "relationships": [],
            }

        record = records[0]

        return {
            "nodes": record.get(
                "nodes",
                [],
            ),
            "relationships": record.get(
                "relationships",
                [],
            ),
        }

    # ========================================================
    # GRAPH STATISTICS
    # ========================================================

    def graph_statistics(
        self,
    ) -> dict[str, int]:
        """
        Return basic graph statistics.
        """

        query = """
        MATCH (n)

        OPTIONAL MATCH ()-[r]->()

        RETURN
            count(DISTINCT n) AS nodes,
            count(DISTINCT r) AS relationships
        """

        records = self.client.execute_read(query)

        if not records:
            return {
                "nodes": 0,
                "relationships": 0,
            }

        return {
            "nodes": records[0]["nodes"],
            "relationships": records[0]["relationships"],
        }

    # ========================================================
    # RELATIONSHIP TYPES
    # ========================================================

    def relationship_types(
        self,
    ) -> list[str]:
        """
        Return relationship types currently present.
        """

        query = """
        MATCH ()-[r]->()

        RETURN DISTINCT
            type(r) AS relationship_type

        ORDER BY relationship_type
        """

        records = self.client.execute_read(query)

        return [
            record["relationship_type"]
            for record in records
        ]

    # ========================================================
    # ENTITY TYPES
    # ========================================================

    def entity_types(
        self,
    ) -> list[str]:
        """
        Return entity types currently present.
        """

        query = """
        MATCH (n:Entity)

        RETURN DISTINCT
            n.entity_type AS entity_type

        ORDER BY entity_type
        """

        records = self.client.execute_read(query)

        return [
            record["entity_type"]
            for record in records
        ]

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _records_to_dicts(
        records: list[Record],
    ) -> list[dict[str, Any]]:
        """
        Convert Neo4j records to normal dictionaries.
        """

        return [
            dict(record)
            for record in records
        ]

    @staticmethod
    def _validate_depth(
        depth: int,
        maximum: int = 6,
    ) -> int:
        """
        Validate graph traversal depth.
        """

        if not isinstance(depth, int):
            raise TypeError(
                "Graph depth must be an integer."
            )

        if depth < 1:
            raise ValueError(
                "Graph depth must be at least 1."
            )

        if depth > maximum:
            raise ValueError(
                f"Graph depth cannot exceed {maximum}."
            )

        return depth


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

GraphQueryService = GraphQueries


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def find_entity(
    client: Neo4jClient,
    entity_type: str,
    value: str,
) -> list[dict[str, Any]]:
    """
    Convenience wrapper for finding an entity.
    """

    queries = GraphQueries(client)

    return queries.find_entity(
        entity_type=entity_type,
        value=value,
    )


def get_case_entities(
    client: Neo4jClient,
    case_value: str,
) -> list[dict[str, Any]]:
    """
    Convenience wrapper for case graph lookup.
    """

    queries = GraphQueries(client)

    return queries.get_case_entities(
        case_value=case_value,
    )


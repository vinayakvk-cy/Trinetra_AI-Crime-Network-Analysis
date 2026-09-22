"""
TRINETRA Graph Builder
======================

Builds the investigation graph in Neo4j from extracted entities
and relationship candidates.

Responsibilities
----------------
- Create/update entity nodes
- Create/update graph relationships
- Preserve source information
- Store confidence values
- Prevent unnecessary duplicate nodes

This module does NOT:
- Extract entities
- Extract relationships
- Perform graph analytics
- Determine guilt or criminal responsibility
"""

from __future__ import annotations

from typing import Any, Iterable

from app.graph.neo4j_client import Neo4jClient
from app.nlp.entity_extractor import EntityCandidate
from app.nlp.relation_extractor import RelationCandidate


class GraphBuilder:
    """
    Builds and updates the TRINETRA investigation graph.
    """

    def __init__(
        self,
        client: Neo4jClient,
    ) -> None:

        self.client = client

    def _sanitize_relationship_type(
            self,
            relationship_type: str,
        ) -> str:
            """
            Convert a relationship type into a safe Neo4j
            relationship token.
            """

            sanitized = (
                relationship_type.strip()
                .upper()
                .replace("-", "_")
                .replace(" ", "_")
            )

            if not sanitized:
                raise ValueError(
                    "Relationship type cannot be empty."
                )

            if not sanitized.replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid relationship type: {relationship_type}"
                )

            if sanitized[0].isdigit():
                raise ValueError(
                    f"Invalid relationship type: {relationship_type}"
                )

            return sanitized

    # ========================================================
    # ENTITY
    # ========================================================

    def create_entity(
        self,
        entity: EntityCandidate,
    ) -> dict[str, Any]:
        """
        Create or update an entity node.

        Nodes use MERGE so repeated ingestion does not create
        duplicate nodes for the same normalized entity.
        """

        query = """
        MERGE (n:Entity {
            entity_type: $entity_type,
            normalized_value: $normalized_value
        })

        SET
            n.value = $value,
            n.source_field = $source_field,
            n.updated_at = datetime()

        RETURN
            elementId(n) AS node_id,
            n.entity_type AS entity_type,
            n.value AS value,
            n.normalized_value AS normalized_value
        """

        parameters = {
            "entity_type": entity.entity_type,
            "normalized_value": (
                entity.normalized_value
                or entity.value.lower()
            ),
            "value": entity.value,
            "source_field": entity.source_field,
        }

        records = self.client.execute_write(
            query,
            parameters,
        )

        if not records:
            return {}

        return dict(records[0])

    # ========================================================
    # MANY ENTITIES
    # ========================================================

    def create_entities(
        self,
        entities: Iterable[EntityCandidate],
    ) -> list[dict[str, Any]]:
        """
        Create or update multiple entity nodes.
        """

        results: list[
            dict[str, Any]
        ] = []

        for entity in entities:

            results.append(
                self.create_entity(entity)
            )

        return results

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    def create_relationship(
        self,
        relation: RelationCandidate,
    ) -> dict[str, Any]:
        source = relation.source_entity
        target = relation.target_entity

        relationship_type = self._sanitize_relationship_type(
            relation.relation_type
        )

        query = f"""
        MATCH (source:Entity)
        WHERE source.entity_type = $source_type
          AND source.normalized_value = $source_value

        MATCH (target:Entity)
        WHERE target.entity_type = $target_type
          AND target.normalized_value = $target_value

        MERGE (source)-[r:{relationship_type}]->(target)

        SET
            r.confidence = $confidence,
            r.evidence_text = $evidence_text,
            r.source_field = $source_field,
            r.updated_at = datetime()

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
        """

        records = self.client.execute_write(
            query,
            {
                "source_type": source.entity_type.strip().lower(),
                "source_value": source.value.strip().lower(),
                "target_type": target.entity_type.strip().lower(),
                "target_value": target.value.strip().lower(),
                "confidence": relation.confidence,
                "evidence_text": relation.evidence_text,
                "source_field": relation.source_field,
            },
        )

        if not records:
            return {}

        return dict(records[0])

    # ========================================================
    # MANY RELATIONSHIPS
    # ========================================================

    def create_relationships(
        self,
        relations: Iterable[RelationCandidate],
    ) -> list[dict[str, Any]]:
        """
        Create or update multiple relationships.
        """

        results: list[
            dict[str, Any]
        ] = []

        for relation in relations:

            results.append(
                self.create_relationship(
                    relation
                )
            )

        return results

    # ========================================================
    # BUILD GRAPH
    # ========================================================

    def build(
        self,
        entities: Iterable[EntityCandidate],
        relations: Iterable[RelationCandidate],
    ) -> dict[str, Any]:
        """
        Build a graph from entities and relationships.

        Entities are created first so relationship creation can
        safely MATCH them afterward.
        """

        entities = list(entities)
        relations = list(relations)

        entity_results = (
            self.create_entities(
                entities
            )
        )

        relationship_results = (
            self.create_relationships(
                relations
            )
        )

        return {
            "entities_processed": len(
                entity_results
            ),
            "relationships_processed": len(
                relationship_results
            ),
            "entity_results": entity_results,
            "relationship_results": (
                relationship_results
            ),
        }

    # ========================================================
    # DELETE ENTITY
    # ========================================================

    def delete_entity(
        self,
        entity: EntityCandidate,
    ) -> bool:
        """
        Delete an entity and its relationships.

        Use carefully. This is intended mainly for cleanup or
        controlled data-management operations.
        """

        query = """
        MATCH (n:Entity {
            entity_type: $entity_type,
            normalized_value: $normalized_value
        })

        DETACH DELETE n

        RETURN count(n) AS deleted
        """

        parameters = {
            "entity_type": entity.entity_type,
            "normalized_value": (
                entity.normalized_value
                or entity.value.lower()
            ),
        }

        records = self.client.execute_write(
            query,
            parameters,
        )

        if not records:
            return False

        return records[0]["deleted"] > 0

    # ========================================================
    # CLEAR GRAPH
    # ========================================================

    def clear_graph(
        self,
    ) -> int:
        """
        Delete all nodes and relationships.

        WARNING:
        This removes the entire current graph.

        Keep this method for development/testing only.
        """

        query = """
        MATCH (n)
        DETACH DELETE n
        RETURN count(n) AS deleted
        """

        records = self.client.execute_write(
            query
        )

        if not records:
            return 0

        return records[0]["deleted"]

    # ========================================================
    # STATISTICS
    # ========================================================

    def graph_statistics(
        self,
    ) -> dict[str, int]:
        """
        Return basic graph statistics.
        """

        node_query = """
        MATCH (n)
        RETURN count(n) AS count
        """

        relationship_query = """
        MATCH ()-[r]->()
        RETURN count(r) AS count
        """

        node_records = self.client.execute_read(
            node_query
        )

        relationship_records = (
            self.client.execute_read(
                relationship_query
            )
        )

        node_count = (
            node_records[0]["count"]
            if node_records
            else 0
        )

        relationship_count = (
            relationship_records[0]["count"]
            if relationship_records
            else 0
        )

        return {
            "nodes": node_count,
            "relationships": relationship_count,
        }

    # ========================================================
    # RELATIONSHIP TYPE VALIDATION
    # ========================================================

    @staticmethod
    def _safe_relationship_type(
        relation_type: str,
    ) -> str:
        """
        Validate a relationship type before placing it into
        a Cypher query.

        Relationship types cannot be passed as normal Cypher
        parameters, so strict validation is important.
        """

        if not relation_type:
            raise ValueError(
                "Relationship type cannot be empty."
            )

        cleaned = relation_type.strip().upper()

        if not all(
            character.isalnum()
            or character == "_"
            for character in cleaned
        ):
            raise ValueError(
                "Invalid Neo4j relationship type."
            )

        return cleaned


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def build_graph(
    client: Neo4jClient,
    entities: Iterable[EntityCandidate],
    relations: Iterable[RelationCandidate],
) -> dict[str, Any]:
    """
    Convenience function for building a graph.
    """

    builder = GraphBuilder(client)

    return builder.build(
        entities=entities,
        relations=relations,
    )
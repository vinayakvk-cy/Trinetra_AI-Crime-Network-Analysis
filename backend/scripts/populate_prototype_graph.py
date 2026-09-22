from __future__ import annotations

from app.core.config import settings
from app.graph.neo4j_client import Neo4jClient
from app.graph.graph_builder import GraphBuilder
from app.nlp.entity_extractor import EntityCandidate
from app.nlp.relation_extractor import (
    RelationCandidate,
    PERSON_IN_CASE,
    ASSOCIATED_WITH,
    RELATED_TO,
)


CASE_NUMBER = "TRI-PROT-001"

CASE = EntityCandidate(
    entity_type="CASE",
    value=CASE_NUMBER,
    normalized_value=CASE_NUMBER.lower(),
    source_text="Prototype Investigation",
    confidence=1.0,
    source_field="prototype",
)

AARAV = EntityCandidate(
    entity_type="PERSON",
    value="Aarav Sharma",
    normalized_value="aarav sharma",
    source_text="Prototype Intelligence Investigation",
    confidence=0.98,
    source_field="prototype",
)

MEERA = EntityCandidate(
    entity_type="PERSON",
    value="Meera Rao",
    normalized_value="meera rao",
    source_text="Prototype Intelligence Investigation",
    confidence=0.97,
    source_field="prototype",
)

VERTEX = EntityCandidate(
    entity_type="ORGANIZATION",
    value="Vertex Trading Pvt Ltd",
    normalized_value="vertex trading pvt ltd",
    source_text="Prototype Intelligence Investigation",
    confidence=0.96,
    source_field="prototype",
)

HDFC = EntityCandidate(
    entity_type="BANK",
    value="HDFC Bank",
    normalized_value="hdfc bank",
    source_text="Prototype Intelligence Investigation",
    confidence=0.99,
    source_field="prototype",
)


def make_relation(
    relation_type: str,
    source: EntityCandidate,
    target: EntityCandidate,
    confidence: float,
    evidence_text: str,
) -> RelationCandidate:
    return RelationCandidate(
        relation_type=relation_type,
        source_entity=source,
        target_entity=target,
        confidence=confidence,
        evidence_text=evidence_text,
        source_field="prototype",
    )


def main() -> None:
    print("=" * 70)
    print("TRINETRA prototype Neo4j graph population")
    print("=" * 70)

    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )

    try:
        print("\n[1/5] Checking Neo4j connection...")
        if not client.health_check():
            raise RuntimeError("Neo4j health check failed.")

        print("      Neo4j connection: OK")

        builder = GraphBuilder(client)

        print("\n[2/5] Clearing existing Neo4j graph...")
        deleted = builder.clear_graph()
        print(f"      Cleared graph records: {deleted}")

        entities = [
            CASE,
            AARAV,
            MEERA,
            VERTEX,
            HDFC,
        ]

        print("\n[3/5] Creating prototype entities...")
        entity_results = builder.create_entities(entities)

        for result in entity_results:
            print(
                "      Created:",
                result.get("entity_type"),
                "->",
                result.get("value"),
            )

        relations = [
            # Case membership
            make_relation(
                PERSON_IN_CASE,
                AARAV,
                CASE,
                0.95,
                "Aarav Sharma is associated with prototype case TRI-PROT-001.",
            ),
            make_relation(
                PERSON_IN_CASE,
                MEERA,
                CASE,
                0.92,
                "Meera Rao is associated with prototype case TRI-PROT-001.",
            ),

            # Investigation/entity associations
            make_relation(
                ASSOCIATED_WITH,
                AARAV,
                MEERA,
                0.92,
                "Aarav Sharma is known to and communicates with Meera Rao.",
            ),
            make_relation(
                ASSOCIATED_WITH,
                AARAV,
                VERTEX,
                0.88,
                "Aarav Sharma is associated with Vertex Trading Pvt Ltd.",
            ),
            make_relation(
                ASSOCIATED_WITH,
                MEERA,
                VERTEX,
                0.84,
                "Meera Rao is associated with Vertex Trading Pvt Ltd.",
            ),

            # Financial relationship
            make_relation(
                RELATED_TO,
                VERTEX,
                HDFC,
                0.91,
                "Vertex Trading Pvt Ltd transferred funds to HDFC Bank.",
            ),
        ]

        print("\n[4/5] Creating prototype relationships...")
        relationship_results = builder.create_relationships(relations)

        for result in relationship_results:
            print(
                "      Created:",
                result.get("relationship_type"),
                "confidence=",
                result.get("confidence"),
            )

        print("\n[5/5] Reading final graph statistics...")
        stats = builder.graph_statistics()

        print(f"      Nodes: {stats.get('nodes', 0)}")
        print(f"      Relationships: {stats.get('relationships', 0)}")

        print("\n" + "=" * 70)
        print("Prototype graph population complete.")
        print("=" * 70)

    finally:
        client.close()


if __name__ == "__main__":
    main()
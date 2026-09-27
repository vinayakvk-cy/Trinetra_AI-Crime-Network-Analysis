"""
Unit tests for Criminal Network Relationship Extraction.
Tests detection of ACCOMPLICE_OF and crime-related ties between suspects.
"""

from app.nlp.entity_extractor import EntityExtractor
from app.nlp.relation_extractor import RelationExtractor, ACCOMPLICE_OF


def extract_relations(text: str):
    """Helper to extract relations from raw investigation text."""
    entity_extractor = EntityExtractor()
    extraction_result = entity_extractor.extract(text)

    relation_extractor = RelationExtractor()
    result = relation_extractor.extract(text, extraction_result)

    return result.relations


def relation_tuples(relations):
    """Helper to convert relations into easy-to-assert tuples: (type, source, target)."""
    return {
        (
            relation.relation_type,
            relation.source_entity.value,
            relation.target_entity.value,
        )
        for relation in relations
    }


def test_accomplice_of_relation():
    text = "Vikram Malhotra was identified as an accomplice of Rajesh Verma in the robbery."
    relations = extract_relations(text)

    assert (
        "ACCOMPLICE_OF",
        "Vikram Malhotra",
        "Rajesh Verma",
    ) in relation_tuples(relations)


def test_conspired_with_relation():
    text = "Arjun Rao conspired with Kabir Khan during the procurement breach."
    relations = extract_relations(text)

    assert (
        "ACCOMPLICE_OF",
        "Arjun Rao",
        "Kabir Khan",
    ) in relation_tuples(relations)


def test_co_conspirator_relation():
    text = "Suresh Raina was named as a co-conspirator of Dinesh Karthik."
    relations = extract_relations(text)

    assert (
        "ACCOMPLICE_OF",
        "Suresh Raina",
        "Dinesh Karthik",
    ) in relation_tuples(relations)


def test_accomplice_of_model_and_ingestion_type():
    from app.models.entity_relationship import EntityRelationshipType
    from app.intelligence.evidence_ingestion import EvidenceIngestionService

    assert EntityRelationshipType.ACCOMPLICE_OF == "accomplice_of"
    assert (
        EvidenceIngestionService._relationship_type("ACCOMPLICE_OF")
        == EntityRelationshipType.ACCOMPLICE_OF
    )
    assert (
        EvidenceIngestionService._relationship_type("accomplice_of")
        == EntityRelationshipType.ACCOMPLICE_OF
    )

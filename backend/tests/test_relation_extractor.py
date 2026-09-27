from app.nlp.entity_extractor import EntityExtractor
from app.nlp.relation_extractor import RelationExtractor


def extract_relations(text: str):
    entity_extractor = EntityExtractor()
    extraction_result = entity_extractor.extract(text)

    relation_extractor = RelationExtractor()
    result = relation_extractor.extract(
        text,
        extraction_result,
    )

    return result.relations


def relation_tuples(relations):
    return {
        (
            relation.relation_type,
            relation.source_entity.value,
            relation.target_entity.value,
        )
        for relation in relations
    }


def test_knows_relation():
    text = (
        "Aarav Sharma is known to Meera Rao."
    )

    relations = extract_relations(text)

    assert (
        "KNOWS",
        "Aarav Sharma",
        "Meera Rao",
    ) in relation_tuples(relations)


def test_works_for_relation():
    text = (
        "Aarav Sharma works for "
        "Vertex Trading Pvt Ltd."
    )

    relations = extract_relations(text)

    assert (
        "WORKS_FOR",
        "Aarav Sharma",
        "Vertex Trading Pvt Ltd",
    ) in relation_tuples(relations)


def test_contacted_relation():
    text = (
        "Aarav Sharma contacted HDFC Bank."
    )

    relations = extract_relations(text)

    assert (
        "CONTACTED",
        "Aarav Sharma",
        "HDFC Bank",
    ) in relation_tuples(relations)


def test_transferred_to_relation():
    text = (
        "Vertex Trading Pvt Ltd transferred "
        "funds to HDFC Bank."
    )

    relations = extract_relations(text)

    assert (
        "TRANSFERRED_TO",
        "Vertex Trading Pvt Ltd",
        "HDFC Bank",
    ) in relation_tuples(relations)
from app.db.database import SessionLocal
from app.models.evidence import Evidence
from app.nlp.entity_extractor import EntityExtractor
from app.nlp.relation_extractor import RelationExtractor

db = SessionLocal()

try:
    evidence_rows = (
        db.query(Evidence)
        .filter(Evidence.case_id == 1)
        .order_by(Evidence.id)
        .all()
    )

    entity_extractor = EntityExtractor()
    relation_extractor = RelationExtractor()

    for evidence in evidence_rows:
        print("=" * 80)
        print(f"EVIDENCE ID: {evidence.id}")
        print(f"NUMBER:     {evidence.evidence_number}")
        print(f"TITLE:      {evidence.title}")
        print("-" * 80)
        print("EXTRACTED TEXT:")
        print(repr(evidence.extracted_text))
        print()

        extraction = entity_extractor.extract(
            evidence.extracted_text or ""
        )

        print("ENTITIES:")
        for entity in extraction.entities:
            print(
                f"  {entity.entity_type:18} "
                f"{entity.value!r:40} "
                f"normalized={entity.normalized_value!r} "
                f"confidence={entity.confidence}"
            )

        print()
        relations = relation_extractor.extract(
            evidence.extracted_text or "",
            extraction,
        )

        print(f"RELATION COUNT: {relations.count}")

        for relation in relations.relations:
            print(
                f"  {relation.relation_type:25} "
                f"{relation.source_entity.value!r} "
                f"-> "
                f"{relation.target_entity.value!r} "
                f"confidence={relation.confidence}"
            )
            print(f"    evidence_text={relation.evidence_text!r}")

        print()

finally:
    db.close()

from app.db.database import SessionLocal
from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from app.models.case_entity import CaseEntity

db = SessionLocal()

try:
    entities = (
        db.query(Entity)
        .join(CaseEntity, CaseEntity.entity_id == Entity.id)
        .filter(CaseEntity.case_id == 1)
        .all()
    )

    relationships = (
        db.query(EntityRelationship)
        .filter(EntityRelationship.evidence_id.in_([1, 2]))
        .all()
    )

    print("=" * 80)
    print("SQL ENTITIES FOR CASE 1")
    print("=" * 80)

    for e in entities:
        print(
            f"ID={e.id:<4} "
            f"TYPE={getattr(e, 'entity_type', None)!s:<18} "
            f"VALUE={getattr(e, 'value', None)!r:<45} "
            f"NORMALIZED={getattr(e, 'normalized_value', None)!r}"
        )

    print()
    print("=" * 80)
    print(f"SQL RELATIONSHIPS FOR EVIDENCE 1/2: {len(relationships)}")
    print("=" * 80)

    for r in relationships:
        print(
            f"ID={r.id:<4} "
            f"SOURCE_ENTITY={r.source_entity_id:<4} "
            f"TARGET_ENTITY={r.target_entity_id:<4} "
            f"TYPE={r.relationship_type!s:<25} "
            f"EVIDENCE={r.evidence_id!s:<4}"
        )

finally:
    db.close()

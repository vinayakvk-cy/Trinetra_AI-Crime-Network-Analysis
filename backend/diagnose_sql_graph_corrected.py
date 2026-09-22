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

    print("=" * 90)
    print("SQL ENTITIES FOR CASE 1")
    print("=" * 90)

    for e in entities:
        entity_type = getattr(e.entity_type, "value", e.entity_type)

        print(
            f"ID={e.id:<4} "
            f"TYPE={str(entity_type):<18} "
            f"NAME={e.name!r:<45} "
            f"NORMALIZED={e.normalized_name!r}"
        )

    print()
    print("=" * 90)
    print(f"SQL RELATIONSHIPS FOR EVIDENCE 1/2: {len(relationships)}")
    print("=" * 90)

    entity_by_id = {e.id: e for e in entities}

    for r in relationships:
        source = entity_by_id.get(r.source_entity_id)
        target = entity_by_id.get(r.target_entity_id)

        source_name = source.name if source else f"ENTITY_ID_{r.source_entity_id}"
        target_name = target.name if target else f"ENTITY_ID_{r.target_entity_id}"

        source_type = (
            getattr(source.entity_type, "value", source.entity_type)
            if source else "?"
        )
        target_type = (
            getattr(target.entity_type, "value", target.entity_type)
            if target else "?"
        )

        relationship_type = getattr(
            r.relationship_type,
            "value",
            r.relationship_type,
        )

        print(
            f"ID={r.id:<4} "
            f"{source_type}:{source_name!r} "
            f"--{relationship_type}--> "
            f"{target_type}:{target_name!r} "
            f"EVIDENCE={r.evidence_id}"
        )

finally:
    db.close()

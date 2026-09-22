from __future__ import annotations

from typing import Any

from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.investigation_evidence import InvestigationEvidence


class InvestigationContext:
    """Investigation-scoped source-of-truth context for reports/AI."""

    def __init__(self, session, investigation_id: int) -> None:
        self.session = session
        self.investigation_id = investigation_id
        self.investigation = session.get(Investigation, investigation_id)
        if self.investigation is None:
            raise ValueError("Investigation not found.")

    @property
    def case_id(self) -> int | None:
        return getattr(self.investigation, "case_id", None)

    def evidence(self, limit: int = 500) -> list[Evidence]:
        return (
            self.session.query(Evidence)
            .join(
                InvestigationEvidence,
                InvestigationEvidence.evidence_id == Evidence.id,
            )
            .filter(
                InvestigationEvidence.investigation_id == self.investigation_id
            )
            .order_by(Evidence.id.asc())
            .limit(limit)
            .all()
        )

    def entities(self, evidence: list[Evidence] | None = None) -> list[Entity]:
        evidence = evidence if evidence is not None else self.evidence()
        evidence_ids = [item.id for item in evidence]
        if not evidence_ids:
            return []

        entities: dict[int, Entity] = {}

        # Entities created/referenced directly by evidence.
        for entity in (
            self.session.query(Entity)
            .filter(Entity.deleted_at.is_(None))
            .all()
        ):
            source_reference = getattr(entity, "source_reference", None) or ""
            if any(source_reference == f"evidence:{eid}" for eid in evidence_ids):
                entities[entity.id] = entity

        # Also include endpoints of relationships whose authoritative evidence
        # belongs to this investigation.
        relationships = (
            self.session.query(EntityRelationship)
            .filter(
                EntityRelationship.evidence_id.in_(evidence_ids),
                EntityRelationship.deleted_at.is_(None),
            )
            .all()
        )
        for rel in relationships:
            for entity_id in (rel.source_entity_id, rel.target_entity_id):
                entity = self.session.get(Entity, entity_id)
                if entity is not None and getattr(entity, "deleted_at", None) is None:
                    entities[entity.id] = entity

        return sorted(entities.values(), key=lambda item: item.id)

    def relationships(self, evidence: list[Evidence] | None = None) -> list[EntityRelationship]:
        evidence = evidence if evidence is not None else self.evidence()
        evidence_ids = [item.id for item in evidence]
        if not evidence_ids:
            return []
        return (
            self.session.query(EntityRelationship)
            .filter(
                EntityRelationship.evidence_id.in_(evidence_ids),
                EntityRelationship.deleted_at.is_(None),
            )
            .order_by(EntityRelationship.id.asc())
            .all()
        )

    @staticmethod
    def enum_value(value: Any) -> Any:
        return getattr(value, "value", value)

    @classmethod
    def serialize_evidence(cls, item: Evidence) -> dict[str, Any]:
        return {
            "id": item.id,
            "case_id": item.case_id,
            "evidence_number": item.evidence_number,
            "title": item.title,
            "description": item.description,
            "evidence_type": cls.enum_value(item.evidence_type),
            "status": cls.enum_value(item.status),
            "source_type": item.source_type,
            "source_reference": item.source_reference,
            "source_file": item.source_file,
            "file_name": item.file_name,
            "file_hash": item.file_hash,
            "mime_type": item.mime_type,
            "file_size": item.file_size,
            "extracted_text": item.extracted_text,
            "extraction_confidence": item.extraction_confidence,
            "forensic_result": item.forensic_result,
            "forensic_confidence": item.forensic_confidence,
        }

    @classmethod
    def serialize_entity(cls, item: Entity) -> dict[str, Any]:
        return {
            "id": item.id,
            "entity_type": cls.enum_value(item.entity_type),
            "name": item.name,
            "normalized_name": item.normalized_name,
            "source": cls.enum_value(item.source),
            "source_reference": item.source_reference,
            "description": item.description,
            "extraction_method": item.extraction_method,
            "extraction_confidence": item.extraction_confidence,
            "linking_confidence": item.linking_confidence,
            "risk_score": getattr(item, "risk_score", None),
            "graph_node_id": item.graph_node_id,
        }

    def serialize_relationship(self, item: EntityRelationship) -> dict[str, Any]:
        source = self.session.get(Entity, item.source_entity_id)
        target = self.session.get(Entity, item.target_entity_id)
        return {
            "id": item.id,
            "source_entity_id": item.source_entity_id,
            "source_entity_type": self.enum_value(source.entity_type) if source else None,
            "source_entity_name": source.name if source else None,
            "target_entity_id": item.target_entity_id,
            "target_entity_type": self.enum_value(target.entity_type) if target else None,
            "target_entity_name": target.name if target else None,
            "relationship_type": self.enum_value(item.relationship_type),
            "description": item.description,
            "confidence": item.confidence,
            "source": item.source,
            "source_reference": item.source_reference,
            "evidence_id": item.evidence_id,
            "notes": item.notes,
        }

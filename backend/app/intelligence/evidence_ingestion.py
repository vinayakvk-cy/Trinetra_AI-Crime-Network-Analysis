from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.graph_builder import GraphBuilder
from app.models.case import Case
from app.models.case_entity import CaseEntity, CaseEntityRelation
from app.models.entity import Entity, EntitySource, EntityType
from app.models.entity_relationship import (
    EntityRelationship,
    EntityRelationshipType,
)
from app.models.evidence import Evidence
from app.nlp.entity_extractor import EntityCandidate, EntityExtractor
from app.nlp.relation_extractor import RelationCandidate, RelationExtractor


# ============================================================
# RESULT
# ============================================================


@dataclass
class EvidenceIngestionResult:
    evidence_id: int

    entities_created: int = 0
    entities_reused: int = 0

    case_entities_created: int = 0
    case_entities_reused: int = 0

    relationships_created: int = 0
    relationships_reused: int = 0

    graph_nodes_synced: int = 0
    graph_relationships_synced: int = 0

    extracted_entities: list[dict[str, Any]] = field(
        default_factory=list
    )

    extracted_relationships: list[dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "entities_created": self.entities_created,
            "entities_reused": self.entities_reused,
            "case_entities_created": self.case_entities_created,
            "case_entities_reused": self.case_entities_reused,
            "relationships_created": self.relationships_created,
            "relationships_reused": self.relationships_reused,
            "graph_nodes_synced": self.graph_nodes_synced,
            "graph_relationships_synced": self.graph_relationships_synced,
            "extracted_entities": self.extracted_entities,
            "extracted_relationships": self.extracted_relationships,
        }


# ============================================================
# SERVICE
# ============================================================


class EvidenceIngestionService:
    """
    Convert evidence text into structured investigative intelligence.

    Pipeline:

        Evidence
            ↓
        EntityExtractor
            ↓
        RelationExtractor
            ↓
        SQL Entity
            ↓
        CaseEntity
            ↓
        EntityRelationship
            ↓
        Neo4j
    """

    def __init__(
        self,
        session: Session,
        neo4j_client=None,
    ):
        self.session = session
        self.db = session

        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

        self.graph_builder = (
            GraphBuilder(neo4j_client)
            if neo4j_client
            else None
        )

    # ========================================================
    # PUBLIC
    # ========================================================

    def ingest_evidence(
        self,
        evidence_id: int,
    ) -> EvidenceIngestionResult:
        evidence = self.session.get(
            Evidence,
            evidence_id,
        )

        if evidence is None:
            raise ValueError(
                f"Evidence {evidence_id} not found."
            )

        text = (
            getattr(evidence, "extracted_text", None)
            or ""
        ).strip()

        if not text:
            raise ValueError(
                f"Evidence {evidence_id} has no extracted text."
            )

        result = EvidenceIngestionResult(
            evidence_id=evidence_id
        )

        # ----------------------------------------------------
        # 1. NLP ENTITY EXTRACTION
        # ----------------------------------------------------

        extraction_result = (
            self.entity_extractor.extract(text)
        )

        # ----------------------------------------------------
        # 2. NLP RELATION EXTRACTION
        # ----------------------------------------------------

        relation_result = (
            self.relation_extractor.extract(
                text,
                extraction_result,
            )
        )

        # ----------------------------------------------------
        # 3. ENTITY PERSISTENCE
        # ----------------------------------------------------

        entity_map: dict[
            tuple[str, str],
            Entity,
        ] = {}

        for candidate in extraction_result.entities:
            entity = self._get_or_create_entity(
                candidate=candidate,
                evidence=evidence,
                result=result,
            )

            if entity is None:
                continue

            key = self._entity_key(
                entity.entity_type,
                entity.normalized_name,
            )

            entity_map[key] = entity

            # Also allow resolution by the candidate's
            # normalized value.
            candidate_key = self._entity_key(
                candidate.entity_type,
                candidate.normalized_value
                or candidate.value,
            )

            entity_map[candidate_key] = entity

            result.extracted_entities.append(
                {
                    "entity_id": entity.id,
                    "entity_type": (
                        entity.entity_type.value
                    ),
                    "name": entity.name,
                    "normalized_name": (
                        entity.normalized_name
                    ),
                    "confidence": (
                        entity.extraction_confidence
                    ),
                }
            )

            # ------------------------------------------------
            # 4. CASE → ENTITY LINK
            # ------------------------------------------------

            self._get_or_create_case_entity(
                evidence=evidence,
                entity=entity,
                result=result,
            )

        # ----------------------------------------------------
        # 5. SQL RELATIONSHIPS
        # ----------------------------------------------------

        for relation in relation_result.relations:
            source_entity = self._resolve_entity(
                relation.source_entity,
                entity_map,
            )

            target_entity = self._resolve_entity(
                relation.target_entity,
                entity_map,
            )

            if source_entity is None:
                continue

            if target_entity is None:
                continue

            relationship = (
                self._get_or_create_relationship(
                    relation=relation,
                    source_entity=source_entity,
                    target_entity=target_entity,
                    evidence=evidence,
                    result=result,
                )
            )

            if relationship is None:
                continue

            result.extracted_relationships.append(
                {
                    "relationship_id": relationship.id,
                    "source_entity_id": (
                        relationship.source_entity_id
                    ),
                    "target_entity_id": (
                        relationship.target_entity_id
                    ),
                    "relationship_type": (
                        relationship.relationship_type.value
                    ),
                    "confidence": (
                        relationship.confidence
                    ),
                    "evidence_id": (
                        relationship.evidence_id
                    ),
                }
            )

        # ----------------------------------------------------
        # 6. COMMIT SQL
        # ----------------------------------------------------

        self.session.commit()

        # ----------------------------------------------------
        # 7. SYNC NEO4J
        # ----------------------------------------------------

        self._sync_graph(
            entity_map,
            relation_result.relations,
            result,
            evidence=evidence,
        )

        return result

    # ========================================================
    # ENTITY
    # ========================================================

    def _get_or_create_entity(
        self,
        candidate: EntityCandidate,
        evidence: Evidence,
        result: EvidenceIngestionResult,
    ) -> Entity | None:
        value = (candidate.value or "").strip()

        if not value:
            return None

        entity_type = self._entity_type(
            candidate.entity_type
        )

        normalized_name = (
            candidate.normalized_value
            or value.lower()
        ).strip().lower()

        if not normalized_name:
            return None

        statement = select(Entity).where(
            Entity.entity_type == entity_type,
            Entity.normalized_name == normalized_name,
        )

        entity = self.session.scalar(statement)

        # ----------------------------------------------------
        # 1. EXACT MATCH
        # ----------------------------------------------------

        if entity is not None:
            result.entities_reused += 1

            candidate_confidence = float(
                candidate.confidence
            )

            current_confidence = (
                entity.extraction_confidence
                or 0.0
            )

            if candidate_confidence > current_confidence:
                entity.extraction_confidence = (
                    candidate_confidence
                )

            return entity

        # ----------------------------------------------------
        # 2. FUZZY OCR MATCH
        # ----------------------------------------------------

        fuzzy_entity, linking_confidence = (
            self._find_fuzzy_entity(
                entity_type=entity_type,
                normalized_name=normalized_name,
            )
        )

        if fuzzy_entity is not None:
            result.entities_reused += 1

            # Store the confidence that the OCR entity
            # refers to this existing canonical entity.
            fuzzy_entity.linking_confidence = (
                linking_confidence
            )

            candidate_confidence = float(
                candidate.confidence
            )

            current_confidence = (
                fuzzy_entity.extraction_confidence
                or 0.0
            )

            if candidate_confidence > current_confidence:
                fuzzy_entity.extraction_confidence = (
                    candidate_confidence
                )

            return fuzzy_entity

        # ----------------------------------------------------
        # 3. CREATE NEW ENTITY
        # ----------------------------------------------------

        entity = Entity(
            entity_type=entity_type,
            name=value,
            normalized_name=normalized_name,
            source=EntitySource.NLP,
            source_reference=(
                f"evidence:{evidence.id}"
            ),
            description=(
                f"Entity extracted from evidence "
                f"{evidence.id}."
            ),
            extraction_method=(
                candidate.metadata.get(
                    "method",
                    "nlp",
                )
            ),
            extraction_confidence=float(
                candidate.confidence
            ),
            linking_confidence=None,
            graph_node_id=None,
        )

        self.session.add(entity)
        self.session.flush()

        result.entities_created += 1

        return entity

    # ========================================================
    # OCR-AWARE ENTITY LINKING
    # ========================================================

    def _find_fuzzy_entity(
        self,
        entity_type: EntityType,
        normalized_name: str,
        threshold: float = 0.84,
    ) -> tuple[Entity | None, float]:
        if not normalized_name:
            return None, 0.0

        statement = select(Entity).where(
            Entity.entity_type == entity_type,
        )

        entities = self.db.execute(
            statement
        ).scalars().all()

        best_entity: Entity | None = None
        best_score = 0.0

        for entity in entities:
            existing_name = (
                entity.normalized_name
                or entity.name
                or ""
            ).strip()

            if not existing_name:
                continue

            score = self._entity_similarity(
                normalized_name,
                existing_name,
            )

            if score < threshold:
                continue

            if not self._has_safe_token_match(
                normalized_name,
                existing_name,
            ):
                continue

            if score > best_score:
                best_entity = entity
                best_score = score

        return best_entity, best_score

    def _has_safe_token_match(
            self, source: str, target: str) -> bool:
        source_tokens = EvidenceIngestionService._link_normalize(source).split()
        target_tokens = EvidenceIngestionService._link_normalize(target).split()

        if not source_tokens or not target_tokens:
            return False

        # Names/entities must have the same number of tokens.
        if len(source_tokens) != len(target_tokens):
            return False

        token_scores: list[float] = []

        for source_token in source_tokens:
            best_token_score = max(
                SequenceMatcher(
                    None,
                    source_token,
                    target_token,
                ).ratio()
                for target_token in target_tokens
            )
            token_scores.append(best_token_score)

        # Require at least one exact token.
        exact_matches = sum(
            1
            for source_token in source_tokens
            if source_token in target_tokens
        )

        if exact_matches == 0:
            return False

        # Require every token to have reasonable similarity.
        if min(token_scores) < 0.65:
            return False

        # Require a strong average match.
        average_token_score = sum(token_scores) / len(token_scores)

        return average_token_score >= 0.80

    @classmethod
    def _entity_similarity(
        cls,
        source: str,
        target: str,
    ) -> float:
        """
        Calculate OCR-aware similarity between two entity names.

        Combines:
        - whole-string similarity
        - token similarity
        - abbreviation normalization
        """

        source_normalized = cls._link_normalize(source)
        target_normalized = cls._link_normalize(target)

        if not source_normalized or not target_normalized:
            return 0.0

        if source_normalized == target_normalized:
            return 1.0

        whole_score = SequenceMatcher(
            None,
            source_normalized,
            target_normalized,
        ).ratio()

        source_tokens = source_normalized.split()
        target_tokens = target_normalized.split()

        token_scores: list[float] = []

        for source_token in source_tokens:
            best_token_score = 0.0

            for target_token in target_tokens:
                token_score = SequenceMatcher(
                    None,
                    source_token,
                    target_token,
                ).ratio()

                best_token_score = max(
                    best_token_score,
                    token_score,
                )

            token_scores.append(best_token_score)

        token_score = (
            sum(token_scores) / len(token_scores)
            if token_scores
            else 0.0
        )

        return (
            (whole_score * 0.60)
            + (token_score * 0.40)
        )

    @staticmethod
    def _link_normalize(value: str) -> str:
        """
        Normalize entity text specifically for entity linking.

        This is separate from the canonical stored normalization.

        It handles common OCR punctuation/spacing noise and
        organization abbreviations.
        """

        value = (
            str(value or "")
            .strip()
            .lower()
        )

        if not value:
            return ""

        # Remove punctuation.
        value = re.sub(
            r"[^a-z0-9\s]",
            " ",
            value,
        )

        # Normalize common OCR/company abbreviations.
        replacements = {
            "ltd": "limited",
            "lid": "limited",
            "pvt": "private",
            "pvtltd": "private limited",
            "co": "company",
            "corp": "corporation",
            "inc": "incorporated",
        }

        tokens = value.split()

        normalized_tokens: list[str] = []

        for token in tokens:
            normalized_tokens.append(
                replacements.get(
                    token,
                    token,
                )
            )

        return " ".join(normalized_tokens)

    # ========================================================
    # CASE → ENTITY
    # ========================================================

    def _get_or_create_case_entity(
        self,
        evidence: Evidence,
        entity: Entity,
        result: EvidenceIngestionResult,
    ) -> CaseEntity | None:
        case_id = getattr(
            evidence,
            "case_id",
            None,
        )

        if not case_id:
            return None

        relation = self._case_entity_relation(
            entity.entity_type
        )

        statement = select(CaseEntity).where(
            CaseEntity.case_id == case_id,
            CaseEntity.entity_id == entity.id,
            CaseEntity.relation == relation,
            CaseEntity.deleted_at.is_(None),
        )

        case_entity = self.session.scalar(
            statement
        )

        if case_entity is not None:
            result.case_entities_reused += 1
            return case_entity

        case_entity = CaseEntity(
            case_id=case_id,
            entity_id=entity.id,
            relation=relation,
            notes=(
                f"Automatically linked from "
                f"evidence {evidence.id}."
            ),
        )

        self.session.add(case_entity)
        self.session.flush()

        result.case_entities_created += 1

        return case_entity

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    def _get_or_create_relationship(
        self,
        relation: RelationCandidate,
        source_entity: Entity,
        target_entity: Entity,
        evidence: Evidence,
        result: EvidenceIngestionResult,
    ) -> EntityRelationship | None:
        if source_entity.id == target_entity.id:
            return None

        relationship_type = (
            self._relationship_type(
                relation.relation_type
            )
        )

        statement = select(
            EntityRelationship
        ).where(
            EntityRelationship.source_entity_id
            == source_entity.id,
            EntityRelationship.target_entity_id
            == target_entity.id,
            EntityRelationship.relationship_type
            == relationship_type,
            EntityRelationship.deleted_at.is_(None),
        )

        existing = self.session.scalar(
            statement
        )

        if existing is not None:
            result.relationships_reused += 1

            candidate_confidence = float(
                relation.confidence
            )

            current_confidence = (
                existing.confidence
                or 0.0
            )

            if candidate_confidence > current_confidence:
                existing.confidence = (
                    candidate_confidence
                )

            if existing.evidence_id is None:
                existing.evidence_id = evidence.id

            return existing

        relationship = EntityRelationship(
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id,
            relationship_type=relationship_type,
            description=relation.evidence_text,
            confidence=float(
                relation.confidence
            ),
            source="nlp",
            source_reference=(
                f"evidence:{evidence.id}"
            ),
            evidence_id=evidence.id,
            notes=(
                "Automatically extracted from "
                "evidence."
            ),
        )

        self.session.add(relationship)
        self.session.flush()

        result.relationships_created += 1

        return relationship

    # ========================================================
    # ENTITY RESOLUTION
    # ========================================================

    def _resolve_entity(
        self,
        candidate: EntityCandidate,
        entity_map: dict[
            tuple[str, str],
            Entity,
        ],
    ) -> Entity | None:
        return entity_map.get(
            self._entity_key(
                candidate.entity_type,
                candidate.normalized_value
                or candidate.value,
            )
        )

    @classmethod
    def _entity_key(
        cls,
        entity_type: str | EntityType,
        value: str | None,
    ) -> tuple[str, str]:
        resolved_type = cls._entity_type(
            entity_type
        )

        normalized = (
            (value or "")
            .strip()
            .lower()
        )

        return (
            resolved_type.value,
            normalized,
        )

    # ========================================================
    # NEO4J
    # ========================================================

    def _sync_graph(
        self,
        entity_map: dict[tuple[str, str], Entity],
        relations: list[RelationCandidate],
        result: EvidenceIngestionResult,
        evidence: Evidence | None = None,
    ) -> None:
        if self.graph_builder is None:
            return

        # ----------------------------------------------------
        # 1. SYNC CASE CONTEXT
        # ----------------------------------------------------
        #
        # Analytics and assistant graph retrieval are
        # investigation/case scoped and expect a CASE node in
        # Neo4j. The relational ingestion pipeline already
        # creates CaseEntity rows, so mirror that authoritative
        # case context into the graph.
        #
        # This is intentionally derived from the case/evidence
        # relationship rather than hard-coded demo data.

        if evidence is not None and getattr(evidence, "case_id", None):
            try:
                case = self.session.get(
                    Case,
                    evidence.case_id,
                )

                if case is not None and getattr(case, "case_number", None):
                    case_candidate = EntityCandidate(
                        entity_type=EntityType.CASE,
                        value=case.case_number,
                        normalized_value=case.case_number.lower(),
                        confidence=1.0,
                        metadata={
                            "method": "canonical_sql_case",
                            "case_id": case.id,
                        },
                    )

                    self.graph_builder.create_entity(
                        case_candidate
                    )

                    case_entities = (
                        self.session.query(CaseEntity)
                        .filter(
                            CaseEntity.case_id == case.id,
                            CaseEntity.deleted_at.is_(None),
                        )
                        .all()
                    )

                    for case_entity in case_entities:
                        entity = self.session.get(
                            Entity,
                            case_entity.entity_id,
                        )

                        if entity is None or getattr(entity, "deleted_at", None) is not None:
                            continue

                        relation_name = getattr(
                            case_entity.relation,
                            "value",
                            str(case_entity.relation),
                        )

                        case_relation = RelationCandidate(
                            source_entity=case_candidate,
                            target_entity=EntityCandidate(
                                entity_type=entity.entity_type,
                                value=entity.name,
                                normalized_value=entity.normalized_name,
                                confidence=entity.extraction_confidence or 0.0,
                                metadata={
                                    "entity_id": entity.id,
                                    "method": "canonical_sql_entity",
                                },
                            ),
                            relation_type=f"CASE_{relation_name.upper()}",
                            confidence=1.0,
                            evidence_text=case_entity.notes,
                            metadata={
                                "case_entity_id": case_entity.id,
                                "case_id": case.id,
                            },
                        )

                        self.graph_builder.create_relationship(
                            case_relation
                        )

            except Exception as exc:
                # SQL remains authoritative if the graph case
                # projection cannot be updated temporarily.
                print(
                    f"[GRAPH SYNC CASE ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

        # ----------------------------------------------------
        # 2. SYNC CANONICAL ENTITIES
        # ----------------------------------------------------

        synced_entity_ids: set[int] = set()

        for entity in entity_map.values():
            if entity.id in synced_entity_ids:
                continue

            try:
                candidate = EntityCandidate(
                    entity_type=entity.entity_type,
                    value=entity.name,
                    normalized_value=entity.normalized_name,
                    confidence=(
                        entity.extraction_confidence or 0.0
                    ),
                    metadata={
                        "method": "canonical_sql_entity",
                        "entity_id": entity.id,
                    },
                )

                self.graph_builder.create_entity(candidate)

                synced_entity_ids.add(entity.id)
                result.graph_nodes_synced += 1

            except Exception:
                # SQL remains authoritative if Neo4j
                # temporarily fails.
                continue

        # ----------------------------------------------------
        # 2. SYNC CANONICAL RELATIONSHIPS
        # ----------------------------------------------------

        for relation in relations:
            try:
                source_entity = self._resolve_entity(
                    relation.source_entity,
                    entity_map,
                )

                target_entity = self._resolve_entity(
                    relation.target_entity,
                    entity_map,
                )

                if source_entity is None:
                    continue

                if target_entity is None:
                    continue

                if source_entity.id == target_entity.id:
                    continue

                canonical_relation = RelationCandidate(
                    source_entity=EntityCandidate(
                        entity_type=source_entity.entity_type,
                        value=source_entity.name,
                        normalized_value=source_entity.normalized_name,
                        confidence=(
                            source_entity.extraction_confidence
                            or 0.0
                        ),
                        metadata={
                            "entity_id": source_entity.id,
                            "method": "canonical_sql_entity",
                        },
                    ),
                    target_entity=EntityCandidate(
                        entity_type=target_entity.entity_type,
                        value=target_entity.name,
                        normalized_value=target_entity.normalized_name,
                        confidence=(
                            target_entity.extraction_confidence
                            or 0.0
                        ),
                        metadata={
                            "entity_id": target_entity.id,
                            "method": "canonical_sql_entity",
                        },
                    ),
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    evidence_text=relation.evidence_text,
                    metadata=getattr(
                        relation,
                        "metadata",
                        {},
                    ),
                )

                self.graph_builder.create_relationship(
                    canonical_relation
                )

                result.graph_relationships_synced += 1

            except Exception as exc:
                print(
                    f"[GRAPH SYNC RELATIONSHIP ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )
            continue

    # ========================================================
    # ENUM HELPERS
    # ========================================================

    @staticmethod
    def _entity_type(
        value: str | EntityType,
    ) -> EntityType:
        if isinstance(value, EntityType):
            return value

        normalized = (
            str(value)
            .strip()
            .lower()
        )

        aliases = {
            "person": EntityType.PERSON,
            "phone": EntityType.PHONE,
            "email": EntityType.EMAIL,
            "vehicle": EntityType.VEHICLE,
            "location": EntityType.LOCATION,
            "address": EntityType.ADDRESS,
            "organization": EntityType.ORGANIZATION,
            "company": EntityType.ORGANIZATION,
            "bank": EntityType.ORGANIZATION,
            "social_account": EntityType.SOCIAL_ACCOUNT,
            "bank_account": EntityType.BANK_ACCOUNT,
            "account": EntityType.BANK_ACCOUNT,
            "transaction": EntityType.TRANSACTION,
            "device": EntityType.DEVICE,
            "case": EntityType.CASE,
            "evidence": EntityType.EVIDENCE,
            "unknown": EntityType.UNKNOWN,
        }

        return aliases.get(
            normalized,
            EntityType.UNKNOWN,
        )

    @staticmethod
    def _relationship_type(
        value: str | EntityRelationshipType,
    ) -> EntityRelationshipType:
        if isinstance(
            value,
            EntityRelationshipType,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .lower()
        )

        aliases = {
            "associated_with":
                EntityRelationshipType.ASSOCIATED_WITH,
            "knows":
                EntityRelationshipType.KNOWS,
            "owns":
                EntityRelationshipType.OWNS,
            "uses":
                EntityRelationshipType.USES,
            "contacted":
                EntityRelationshipType.CONTACTED,
            "called":
                EntityRelationshipType.CALLED,
            "visited":
                EntityRelationshipType.VISITED,
            "located_at":
                EntityRelationshipType.LOCATED_AT,
            "traveled_to":
                EntityRelationshipType.TRAVELED_TO,
            "travelled_to":
                EntityRelationshipType.TRAVELED_TO,
            "works_for":
                EntityRelationshipType.WORKS_FOR,
            "member_of":
                EntityRelationshipType.MEMBER_OF,
            "connected_to":
                EntityRelationshipType.CONNECTED_TO,
            "transferred_to":
                EntityRelationshipType.TRANSFERRED_TO,
            "received_from":
                EntityRelationshipType.RECEIVED_FROM,
            "registered_to":
                EntityRelationshipType.REGISTERED_TO,
            "belongs_to":
                EntityRelationshipType.BELONGS_TO,
            "linked_to":
                EntityRelationshipType.LINKED_TO,
            "related_to":
                EntityRelationshipType.RELATED_TO,
        }

        return aliases.get(
            normalized,
            EntityRelationshipType.OTHER,
        )

    @staticmethod
    def _case_entity_relation(
        entity_type: EntityType,
    ) -> CaseEntityRelation:
        mapping = {
            EntityType.PERSON:
                CaseEntityRelation.PERSON_OF_INTEREST,

            EntityType.VEHICLE:
                CaseEntityRelation.VEHICLE,

            EntityType.LOCATION:
                CaseEntityRelation.LOCATION,

            EntityType.ORGANIZATION:
                CaseEntityRelation.ORGANIZATION,

            EntityType.PHONE:
                CaseEntityRelation.PHONE,

            EntityType.BANK_ACCOUNT:
                CaseEntityRelation.ACCOUNT,

            EntityType.EVIDENCE:
                CaseEntityRelation.EVIDENCE_ENTITY,
        }

        return mapping.get(
            entity_type,
            CaseEntityRelation.RELATED,
        )
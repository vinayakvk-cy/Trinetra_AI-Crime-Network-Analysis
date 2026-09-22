from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.nlp.entity_extractor import (
    EntityCandidate,
    EntityExtractionResult,
    PERSON,
    PHONE,
)


# ============================================================
# RELATIONSHIP TYPES
# ============================================================

RELATED_TO = "RELATED_TO"
ASSOCIATED_WITH = "ASSOCIATED_WITH"
MENTIONED_WITH = "MENTIONED_WITH"

# Prototype investigation relationship types
KNOWS = "KNOWS"
WORKS_FOR = "WORKS_FOR"
CONTACTED = "CONTACTED"
TRANSFERRED_TO = "TRANSFERRED_TO"

PERSON_IN_CASE = "PERSON_IN_CASE"
PERSON_IN_FIR = "PERSON_IN_FIR"

PERSON_USED_PHONE = "PERSON_USED_PHONE"
PERSON_USED_DEVICE = "PERSON_USED_DEVICE"

PERSON_OWNS_VEHICLE = "PERSON_OWNS_VEHICLE"
PERSON_ASSOCIATED_VEHICLE = "PERSON_ASSOCIATED_VEHICLE"

PERSON_AT_LOCATION = "PERSON_AT_LOCATION"
PERSON_AT_TIME = "PERSON_AT_TIME"

DEVICE_AT_LOCATION = "DEVICE_AT_LOCATION"
PHONE_AT_LOCATION = "PHONE_AT_LOCATION"

EVIDENCE_RELATED_CASE = "EVIDENCE_RELATED_CASE"
EVIDENCE_RELATED_PERSON = "EVIDENCE_RELATED_PERSON"

INMATE_RELATED_PERSON = "INMATE_RELATED_PERSON"

CASE_RELATED_FIR = "CASE_RELATED_FIR"

ORGANIZATION_AT_LOCATION = "ORGANIZATION_AT_LOCATION"

TEMPORAL_ASSOCIATION = "TEMPORAL_ASSOCIATION"


SUPPORTED_RELATION_TYPES = {
    RELATED_TO,
    ASSOCIATED_WITH,
    MENTIONED_WITH,

    KNOWS,
    WORKS_FOR,
    CONTACTED,
    TRANSFERRED_TO,

    PERSON_IN_CASE,
    PERSON_IN_FIR,

    PERSON_USED_PHONE,
    PERSON_USED_DEVICE,

    PERSON_OWNS_VEHICLE,
    PERSON_ASSOCIATED_VEHICLE,

    PERSON_AT_LOCATION,
    PERSON_AT_TIME,

    DEVICE_AT_LOCATION,
    PHONE_AT_LOCATION,

    EVIDENCE_RELATED_CASE,
    EVIDENCE_RELATED_PERSON,

    INMATE_RELATED_PERSON,

    CASE_RELATED_FIR,

    ORGANIZATION_AT_LOCATION,

    TEMPORAL_ASSOCIATION,
}


# ============================================================
# RELATIONSHIP CUES
# ============================================================

PHONE_CUES = (
    "phone",
    "mobile",
    "telephone",
    "called",
    "calling",
    "contacted",
    "contact",
)

DEVICE_CUES = (
    "device",
    "imei",
    "gps",
    "tracked",
    "tracking",
    "located",
)

VEHICLE_CUES = (
    "vehicle",
    "car",
    "bike",
    "motorcycle",
    "truck",
    "registration",
    "number plate",
    "license plate",
)

LOCATION_CUES = (
    "at",
    "near",
    "inside",
    "outside",
    "located",
    "location",
    "place",
    "visited",
    "travelled",
    "traveled",
)

OWNERSHIP_CUES = (
    "owned by",
    "belongs to",
    "registered to",
    "owner",
    "owns",
)

ASSOCIATION_CUES = (
    "associated with",
    "linked to",
    "connected to",
    "related to",
    "belonged to",
    "banking relationship with",
)

KNOWS_CUES = (
    "knows",
    "known to",
    "is known to",
    "know each other",
)

WORKS_FOR_CUES = (
    "works for",
    "work for",
    "worked for",
    "works at",
    "worked at",
    "employed by",
    "employee of",
)

CONTACTED_CUES = (
    "contacted",
    "contact",
    "called",
    "calling",
    "communicated with",
    "communication between",
)

TRANSFERRED_TO_CUES = (
    "transferred to",
    "transfer to",
    "sent funds to",
    "transferred funds to",
)

CASE_CUES = (
    "case",
    "investigation",
    "case number",
)

FIR_CUES = (
    "fir",
    "first information report",
)

EVIDENCE_CUES = (
    "evidence",
    "exhibit",
    "seized",
    "recovered",
    "forensic",
)

INMATE_CUES = (
    "inmate",
    "prisoner",
    "jail",
    "custody",
)


# ============================================================
# DATACLASS
# ============================================================


@dataclass
class RelationCandidate:
    """
    Candidate relationship between two entities.

    A candidate relationship is an extracted observation.
    It should not automatically be interpreted as a confirmed
    investigative fact.
    """

    relation_type: str

    source_entity: EntityCandidate

    target_entity: EntityCandidate

    confidence: float = 1.0

    evidence_text: str | None = None

    source_field: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert relationship to dictionary.
        """

        return {
            "relation_type": self.relation_type,
            "source_entity": (
                self.source_entity.to_dict()
            ),
            "target_entity": (
                self.target_entity.to_dict()
            ),
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
            "source_field": self.source_field,
            "metadata": self.metadata,
        }


# ============================================================
# EXTRACTION RESULT
# ============================================================


@dataclass
class RelationExtractionResult:
    """
    Result returned by RelationExtractor.
    """

    relations: list[RelationCandidate]

    source_text: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def count(self) -> int:
        """
        Number of extracted relationships.
        """

        return len(self.relations)

    def by_type(
        self,
        relation_type: str,
    ) -> list[RelationCandidate]:
        """
        Return relationships of a particular type.
        """

        return [
            relation
            for relation in self.relations
            if relation.relation_type
            == relation_type
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary.
        """

        return {
            "count": self.count,
            "relations": [
                relation.to_dict()
                for relation in self.relations
            ],
            "source_text": self.source_text,
            "metadata": self.metadata,
        }


# ============================================================
# RELATION EXTRACTOR
# ============================================================


class RelationExtractor:
    """
    Extracts candidate relationships between entities.

    The extractor uses:
    - entity types
    - source fields
    - nearby text
    - relationship keywords
    - deterministic rules

    A more advanced NLP model can be integrated later while
    preserving the RelationCandidate interface.
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        window_size: int = 120,
    ) -> None:

        self.window_size = max(
            20,
            window_size,
        )

    # ========================================================
    # TEXT
    # ========================================================

    def extract(
        self,
        text: str,
        extraction_result: EntityExtractionResult,
    ) -> RelationExtractionResult:
        """
        Extract candidate relationships from text and its
        previously extracted entities.
        """

        if not text:

            return RelationExtractionResult(
                relations=[],
                source_text=text,
            )

        entities = extraction_result.entities

        relations: list[
            RelationCandidate
        ] = []

        # ----------------------------------------------------
        # Pair-based relationships
        # ----------------------------------------------------

        for index, source in enumerate(
            entities
        ):

            for target in entities[
                index + 1:
            ]:

                if self._same_entity(
                    source,
                    target,
                ):
                    continue

                context = (
                    self._relationship_context(
                        text,
                        source,
                        target,
                    )
                )

                candidate_relations = (
                    self._infer_pair_relations(
                        source=source,
                        target=target,
                        context=context,
                    )
                )

                relations.extend(
                    candidate_relations
                )

        # ----------------------------------------------------
        # Text cue relationships
        # ----------------------------------------------------

        relations.extend(
            self._extract_cue_relationships(
                text,
                entities,
            )
        )

        relations = self._remove_duplicates(
            relations
        )

        return RelationExtractionResult(
            relations=relations,
            source_text=text,
            metadata={
                "extractor": "RelationExtractor",
                "window_size": self.window_size,
            },
        )

    # ========================================================
    # STRUCTURED RECORD
    # ========================================================

    def extract_from_entities(
        self,
        entities: Iterable[EntityCandidate],
    ) -> RelationExtractionResult:
        """
        Generate relationships from entity types alone.

        This is useful when source records are already
        structured and there is no free-text context.
        """

        entities = list(entities)

        relations: list[
            RelationCandidate
        ] = []

        for index, source in enumerate(
            entities
        ):

            for target in entities[
                index + 1:
            ]:

                relation = (
                    self._infer_structured_relation(
                        source,
                        target,
                    )
                )

                if relation:

                    relations.append(
                        relation
                    )

        return RelationExtractionResult(
            relations=self._remove_duplicates(
                relations
            ),
            metadata={
                "extractor": "RelationExtractor",
                "structured_mode": True,
            },
        )

    # ========================================================
    # PAIR RELATIONS
    # ========================================================

    def _infer_pair_relations(
        self,
        source: EntityCandidate,
        target: EntityCandidate,
        context: str,
    ) -> list[RelationCandidate]:
        """
        Infer relationships for a pair of entities.
        """

        relations: list[
            RelationCandidate
        ] = []

        context_lower = context.lower()

        # ----------------------------------------------------
        # PERSON -> PHONE
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "PHONE",
        ):

            if self._contains_any(
                context_lower,
                PHONE_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_USED_PHONE,
                        source,
                        target,
                        0.88,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PERSON -> DEVICE
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "DEVICE",
        ):

            if self._contains_any(
                context_lower,
                DEVICE_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_USED_DEVICE,
                        source,
                        target,
                        0.86,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PERSON -> VEHICLE
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "VEHICLE",
        ):

            if self._contains_any(
                context_lower,
                OWNERSHIP_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_OWNS_VEHICLE,
                        source,
                        target,
                        0.90,
                        context,
                    )
                )

            elif self._contains_any(
                context_lower,
                VEHICLE_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_ASSOCIATED_VEHICLE,
                        source,
                        target,
                        0.75,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PERSON -> LOCATION
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "LOCATION",
        ):

            if self._contains_any(
                context_lower,
                LOCATION_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_AT_LOCATION,
                        source,
                        target,
                        0.82,
                        context,
                    )
                )

        # ----------------------------------------------------
        # DEVICE -> LOCATION
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "DEVICE",
            "LOCATION",
        ):

            if self._contains_any(
                context_lower,
                LOCATION_CUES,
            ):

                relations.append(
                    self._relation(
                        DEVICE_AT_LOCATION,
                        source,
                        target,
                        0.84,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PHONE -> LOCATION
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PHONE",
            "LOCATION",
        ):

            if self._contains_any(
                context_lower,
                LOCATION_CUES,
            ):

                relations.append(
                    self._relation(
                        PHONE_AT_LOCATION,
                        source,
                        target,
                        0.80,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PERSON -> CASE
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "CASE",
        ):

            if self._contains_any(
                context_lower,
                CASE_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_IN_CASE,
                        source,
                        target,
                        0.86,
                        context,
                    )
                )

        # ----------------------------------------------------
        # PERSON -> FIR
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "PERSON",
            "FIR",
        ):

            if self._contains_any(
                context_lower,
                FIR_CUES,
            ):

                relations.append(
                    self._relation(
                        PERSON_IN_FIR,
                        source,
                        target,
                        0.84,
                        context,
                    )
                )

        # ----------------------------------------------------
        # EVIDENCE -> CASE
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "EVIDENCE",
            "CASE",
        ):

            relations.append(
                self._relation(
                    EVIDENCE_RELATED_CASE,
                    source,
                    target,
                    0.85,
                    context,
                )
            )

        # ----------------------------------------------------
        # EVIDENCE -> PERSON
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "EVIDENCE",
            "PERSON",
        ):

            if self._contains_any(
                context_lower,
                EVIDENCE_CUES,
            ):

                relations.append(
                    self._relation(
                        EVIDENCE_RELATED_PERSON,
                        source,
                        target,
                        0.72,
                        context,
                    )
                )

        # ----------------------------------------------------
        # CASE -> FIR
        # ----------------------------------------------------

        if self._is_pair(
            source,
            target,
            "CASE",
            "FIR",
        ):

            relations.append(
                self._relation(
                    CASE_RELATED_FIR,
                    source,
                    target,
                    0.95,
                    context,
                )
            )

        return relations

    # ========================================================
    # STRUCTURED RELATIONS
    # ========================================================

    def _infer_structured_relation(
        self,
        source: EntityCandidate,
        target: EntityCandidate,
    ) -> RelationCandidate | None:
        """
        Infer obvious relationships from entity types when
        textual context is unavailable.
        """

        pair = {
            source.entity_type,
            target.entity_type,
        }

        # ----------------------------------------------------
        # CASE + FIR
        # ----------------------------------------------------

        if pair == {"CASE", "FIR"}:

            if source.entity_type == "CASE":

                return self._relation(
                    CASE_RELATED_FIR,
                    source,
                    target,
                    0.90,
                    None,
                )

            return self._relation(
                CASE_RELATED_FIR,
                target,
                source,
                0.90,
                None,
            )

        # ----------------------------------------------------
        # EVIDENCE + CASE
        # ----------------------------------------------------

        if pair == {"EVIDENCE", "CASE"}:

            if source.entity_type == "EVIDENCE":

                return self._relation(
                    EVIDENCE_RELATED_CASE,
                    source,
                    target,
                    0.85,
                    None,
                )

            return self._relation(
                EVIDENCE_RELATED_CASE,
                target,
                source,
                0.85,
                None,
            )

        return None

    # ========================================================
    # CUE RELATIONSHIPS
    # ========================================================

    def _extract_cue_relationships(
        self,
        text: str,
        entities: list[EntityCandidate],
    ) -> list[RelationCandidate]:
        """
        Extract relationships using sentence-level cues.

        Specific relationship cues are evaluated before the
        generic ASSOCIATED_WITH fallback.
        """

        relations: list[
            RelationCandidate
        ] = []

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text,
        )

        for sentence in sentences:

            sentence_entities = [
                entity
                for entity in entities
                if self._entity_in_text(
                    entity,
                    sentence,
                )
            ]

            if len(sentence_entities) < 2:
                continue

            sentence_lower = sentence.lower()

            # ------------------------------------------------
            # KNOWS
            # ------------------------------------------------

            if self._contains_any(
                sentence_lower,
                KNOWS_CUES,
            ):

                for source, target in (
                    self._pairs(
                        sentence_entities
                    )
                ):

                    if (
                        source.entity_type
                        == "PERSON"
                        and target.entity_type
                        == "PERSON"
                    ):

                        relations.append(
                            self._relation(
                                KNOWS,
                                source,
                                target,
                                0.90,
                                sentence,
                            )
                        )

                continue

            # ------------------------------------------------
            # WORKS_FOR
            # ------------------------------------------------

            if self._contains_any(
                sentence_lower,
                WORKS_FOR_CUES,
            ):

                for source, target in (
                    self._pairs(
                        sentence_entities
                    )
                ):

                    if (
                        source.entity_type
                        == "PERSON"
                        and target.entity_type
                        in {
                            "ORGANIZATION",
                            "COMPANY",
                        }
                    ):

                        relations.append(
                            self._relation(
                                WORKS_FOR,
                                source,
                                target,
                                0.90,
                                sentence,
                            )
                        )

                continue

            # ------------------------------------------------
            # TRANSFERRED_TO
            # ------------------------------------------------

            if self._contains_any(
                sentence_lower,
                TRANSFERRED_TO_CUES,
            ):
                cue_match = re.search(
                    r"\b(?:"
                    r"transferred\s+funds?\s+to"
                    r"|transferred\s+to"
                    r"|transfer\s+to"
                    r"|sent\s+funds?\s+to"
                    r")\b",
                    sentence,
                    re.IGNORECASE,
                )

                if cue_match:
                    cue_start = cue_match.start()
                    cue_end = cue_match.end()

                    before_entities = []
                    after_entities = []

                    for entity in sentence_entities:
                        entity_position = sentence.lower().find(
                            entity.value.lower()
                        )

                        if entity_position < 0:
                            continue

                        if entity_position < cue_start:
                            before_entities.append(
                                (
                                    entity_position,
                                    entity,
                                )
                            )

                        elif entity_position >= cue_end:
                            after_entities.append(
                                (
                                    entity_position,
                                    entity,
                                )
                            )

                    if before_entities and after_entities:
                        # Last entity before the cue = source.
                        source = max(
                            before_entities,
                            key=lambda item: item[0],
                        )[1]

                        # First entity after the cue = destination.
                        target = min(
                            after_entities,
                            key=lambda item: item[0],
                        )[1]

                        if (
                            source.entity_type
                            in {
                                "PERSON",
                                "ORGANIZATION",
                                "COMPANY",
                            }
                            and target.entity_type
                            in {
                                "PERSON",
                                "ORGANIZATION",
                                "COMPANY",
                                "BANK",
                                "ACCOUNT",
                                "TRANSACTION",
                            }
                        ):
                            relations.append(
                                self._relation(
                                    TRANSFERRED_TO,
                                    source,
                                    target,
                                    0.90,
                                    sentence,
                                )
                            )

                continue

            # ------------------------------------------------
            # CONTACTED
            # ------------------------------------------------

            if self._contains_any(
                sentence_lower,
                CONTACTED_CUES,
            ):

                for source, target in (
                    self._pairs(
                        sentence_entities
                    )
                ):

                    if (
                        source.entity_type
                        == "PERSON"
                        and target.entity_type
                        == "PERSON"
                    ):

                        # Communication between two people
                        # is treated as a KNOWS candidate.
                        relations.append(
                            self._relation(
                                KNOWS,
                                source,
                                target,
                                0.82,
                                sentence,
                            )
                        )

                    else:

                        relations.append(
                            self._relation(
                                CONTACTED,
                                source,
                                target,
                                0.82,
                                sentence,
                            )
                        )

                continue

            # ------------------------------------------------
            # ASSOCIATED_WITH
            # ------------------------------------------------

            if self._contains_any(
                sentence_lower,
                ASSOCIATION_CUES,
            ):
                cue_match = None

                for cue in sorted(
                    ASSOCIATION_CUES,
                    key=len,
                    reverse=True,
                ):
                    match = re.search(
                        re.escape(cue),
                        sentence,
                        re.IGNORECASE,
                    )

                    if match:
                        cue_match = match
                        break

                if cue_match:
                    cue_start = cue_match.start()
                    cue_end = cue_match.end()

                    before_entities = []
                    after_entities = []

                    for entity in sentence_entities:
                        entity_position = sentence.lower().find(
                            entity.value.lower()
                        )

                        if entity_position < 0:
                            continue

                        if entity_position < cue_start:
                            before_entities.append(
                                (
                                    entity_position,
                                    entity,
                                )
                            )

                        elif entity_position >= cue_end:
                            after_entities.append(
                                (
                                    entity_position,
                                    entity,
                                )
                            )

                    if before_entities and after_entities:
                        source = max(
                            before_entities,
                            key=lambda item: item[0],
                        )[1]

                        target = min(
                            after_entities,
                            key=lambda item: item[0],
                        )[1]

                        relations.append(
                            self._relation(
                                ASSOCIATED_WITH,
                                source,
                                target,
                                0.78,
                                sentence,
                            )
                        )

                continue

            # ------------------------------------------------
            # Mentioned together
            # ------------------------------------------------

            for source, target in (
                self._pairs(
                    sentence_entities
                )
            ):

                relation = (
                    self._infer_pair_relations(
                        source,
                        target,
                        sentence,
                    )
                )

                if relation:

                    relations.extend(
                        relation
                    )

                else:

                    relations.append(
                        self._relation(
                            MENTIONED_WITH,
                            source,
                            target,
                            0.45,
                            sentence,
                        )
                    )

        return relations

    # ========================================================
    # CONTEXT
    # ========================================================

    def _relationship_context(
        self,
        text: str,
        source: EntityCandidate,
        target: EntityCandidate,
    ) -> str:
        """
        Return text surrounding the two entities.
        """

        positions = []

        if source.start is not None:
            positions.append(source.start)

        if target.start is not None:
            positions.append(target.start)

        if not positions:
            return text[: self.window_size * 2]

        start = max(
            0,
            min(positions) - self.window_size,
        )

        end = min(
            len(text),
            max(positions) + self.window_size,
        )

        return text[start:end]

    # ========================================================
    # ENTITY IN TEXT
    # ========================================================

    @staticmethod
    def _entity_in_text(
        entity: EntityCandidate,
        text: str,
    ) -> bool:
        """
        Check whether an entity value appears in text.
        """

        return (
            entity.value.lower()
            in text.lower()
        )

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _contains_any(
        text: str,
        values: Iterable[str],
    ) -> bool:
        """
        Return True if any cue appears in text.
        """

        return any(
            value.lower() in text
            for value in values
        )

    @staticmethod
    def _is_pair(
        source: EntityCandidate,
        target: EntityCandidate,
        source_type: str,
        target_type: str,
    ) -> bool:
        """
        Check ordered entity pair.
        """

        return (
            source.entity_type == source_type
            and target.entity_type == target_type
        )

    @staticmethod
    def _types_match(
        source: EntityCandidate,
        source_type: str,
        target_type: str,
    ) -> bool:
        """
        Compatibility helper for ordered entity pairs.

        This replaces the previous implementation where the
        target_type parameter was accidentally compared with
        itself.
        """

        return (
            source.entity_type == source_type
            and target_type is not None
        )

    @staticmethod
    def _same_entity(
        first: EntityCandidate,
        second: EntityCandidate,
    ) -> bool:
        """
        Check whether two candidates represent the same
        extracted occurrence.
        """

        if first is second:
            return True

        if (
            first.start is not None
            and second.start is not None
            and first.end is not None
            and second.end is not None
        ):

            return (
                first.start == second.start
                and first.end == second.end
            )

        return (
            first.entity_type
            == second.entity_type
            and first.normalized_value
            == second.normalized_value
        )

    @staticmethod
    def _pairs(
        entities: list[EntityCandidate],
    ):
        """
        Yield unique entity pairs.
        """

        for index, source in enumerate(
            entities
        ):

            for target in entities[
                index + 1:
            ]:

                yield source, target

    # ========================================================
    # RELATION CREATION
    # ========================================================

    @staticmethod
    def _relation(
        relation_type: str,
        source: EntityCandidate,
        target: EntityCandidate,
        confidence: float,
        evidence_text: str | None,
    ) -> RelationCandidate:
        """
        Construct a relationship candidate.
        """

        return RelationCandidate(
            relation_type=relation_type,
            source_entity=source,
            target_entity=target,
            confidence=confidence,
            evidence_text=evidence_text,
            source_field=(
                source.source_field
                or target.source_field
            ),
        )

    # ========================================================
    # DUPLICATE REMOVAL
    # ========================================================

    @staticmethod
    def _remove_duplicates(
        relations: Iterable[
            RelationCandidate
        ],
    ) -> list[RelationCandidate]:
        """
        Remove duplicate relationship candidates.
        """

        result: list[
            RelationCandidate
        ] = []

        seen: set[
            tuple[str, str, str]
        ] = set()

        for relation in relations:

            source_key = (
                relation.source_entity
                .normalized_value
                or relation.source_entity.value.lower()
            )

            target_key = (
                relation.target_entity
                .normalized_value
                or relation.target_entity.value.lower()
            )

            key = (
                relation.relation_type,
                source_key,
                target_key,
            )

            if key in seen:
                continue

            seen.add(key)

            result.append(
                relation
            )

        return result


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def extract_relations(
    text: str,
    extraction_result: EntityExtractionResult,
) -> RelationExtractionResult:
    """
    Convenience function for text-based relationship extraction.
    """

    extractor = RelationExtractor()

    return extractor.extract(
        text=text,
        extraction_result=extraction_result,
    )


def extract_relations_from_entities(
    entities: Iterable[EntityCandidate],
) -> RelationExtractionResult:
    """
    Convenience function for structured relationship extraction.
    """

    extractor = RelationExtractor()

    return extractor.extract_from_entities(
        entities
    )
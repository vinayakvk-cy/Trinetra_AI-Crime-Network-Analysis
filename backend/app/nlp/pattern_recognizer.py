"""
TRINETRA Pattern Recognizer
===========================

Detects investigation-relevant patterns from extracted entities
and relationships.

Responsibilities
----------------
- Detect repeated entities
- Detect repeated contacts
- Detect location patterns
- Detect device/phone associations
- Detect recurring case/evidence associations
- Detect simple temporal patterns
- Produce explainable pattern candidates

This module does NOT:
- determine guilt
- determine criminal intent
- assign final risk
- make legal conclusions
- automatically label a person as a suspect
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable

from app.nlp.entity_extractor import EntityCandidate
from app.nlp.relation_extractor import RelationCandidate


# ============================================================
# PATTERN TYPES
# ============================================================

REPEATED_ENTITY = "REPEATED_ENTITY"
REPEATED_PERSON = "REPEATED_PERSON"
REPEATED_PHONE = "REPEATED_PHONE"
REPEATED_DEVICE = "REPEATED_DEVICE"
REPEATED_LOCATION = "REPEATED_LOCATION"

PERSON_PHONE_ASSOCIATION = "PERSON_PHONE_ASSOCIATION"
PERSON_DEVICE_ASSOCIATION = "PERSON_DEVICE_ASSOCIATION"
PERSON_VEHICLE_ASSOCIATION = "PERSON_VEHICLE_ASSOCIATION"

PERSON_LOCATION_PATTERN = "PERSON_LOCATION_PATTERN"
DEVICE_LOCATION_PATTERN = "DEVICE_LOCATION_PATTERN"

CASE_EVIDENCE_PATTERN = "CASE_EVIDENCE_PATTERN"
CASE_PERSON_PATTERN = "CASE_PERSON_PATTERN"

MULTIPLE_PERSONS_SHARED_PHONE = "MULTIPLE_PERSONS_SHARED_PHONE"
MULTIPLE_PERSONS_SHARED_DEVICE = "MULTIPLE_PERSONS_SHARED_DEVICE"
MULTIPLE_PERSONS_SHARED_LOCATION = "MULTIPLE_PERSONS_SHARED_LOCATION"

RECURRING_RELATIONSHIP = "RECURRING_RELATIONSHIP"


SUPPORTED_PATTERN_TYPES = {
    REPEATED_ENTITY,
    REPEATED_PERSON,
    REPEATED_PHONE,
    REPEATED_DEVICE,
    REPEATED_LOCATION,
    PERSON_PHONE_ASSOCIATION,
    PERSON_DEVICE_ASSOCIATION,
    PERSON_VEHICLE_ASSOCIATION,
    PERSON_LOCATION_PATTERN,
    DEVICE_LOCATION_PATTERN,
    CASE_EVIDENCE_PATTERN,
    CASE_PERSON_PATTERN,
    MULTIPLE_PERSONS_SHARED_PHONE,
    MULTIPLE_PERSONS_SHARED_DEVICE,
    MULTIPLE_PERSONS_SHARED_LOCATION,
    RECURRING_RELATIONSHIP,
}


# ============================================================
# PATTERN CANDIDATE
# ============================================================


@dataclass
class PatternCandidate:
    """
    Represents an observed pattern.

    A pattern is an analytical observation, not a conclusion.
    """

    pattern_type: str

    description: str

    entities: list[EntityCandidate] = field(
        default_factory=list
    )

    relations: list[RelationCandidate] = field(
        default_factory=list
    )

    confidence: float = 0.0

    occurrences: int = 1

    evidence: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert pattern to dictionary.
        """

        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "entities": [
                entity.to_dict()
                for entity in self.entities
            ],
            "relations": [
                relation.to_dict()
                for relation in self.relations
            ],
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


# ============================================================
# RESULT
# ============================================================


@dataclass
class PatternRecognitionResult:
    """
    Result returned by PatternRecognizer.
    """

    patterns: list[PatternCandidate]

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def count(self) -> int:
        """
        Number of detected patterns.
        """

        return len(self.patterns)

    def by_type(
        self,
        pattern_type: str,
    ) -> list[PatternCandidate]:
        """
        Return patterns of a specific type.
        """

        return [
            pattern
            for pattern in self.patterns
            if pattern.pattern_type
            == pattern_type
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary.
        """

        return {
            "count": self.count,
            "patterns": [
                pattern.to_dict()
                for pattern in self.patterns
            ],
            "metadata": self.metadata,
        }


# ============================================================
# PATTERN RECOGNIZER
# ============================================================


class PatternRecognizer:
    """
    Detects simple, explainable patterns from entities and
    relationships.

    The recognizer intentionally uses deterministic rules.
    More advanced statistical/ML pattern detection can be
    added later in the analytics layer.
    """

    def __init__(
        self,
        repeated_threshold: int = 2,
    ) -> None:

        self.repeated_threshold = max(
            2,
            repeated_threshold,
        )

    # ========================================================
    # MAIN ENTRY POINT
    # ========================================================

    def recognize(
        self,
        entities: Iterable[EntityCandidate],
        relations: Iterable[RelationCandidate] = (),
    ) -> PatternRecognitionResult:
        """
        Detect patterns from entities and relationships.
        """

        entities = list(entities)
        relations = list(relations)

        patterns: list[
            PatternCandidate
        ] = []

        patterns.extend(
            self._detect_repeated_entities(
                entities
            )
        )

        patterns.extend(
            self._detect_relationship_patterns(
                relations
            )
        )

        patterns.extend(
            self._detect_shared_phone_patterns(
                entities,
                relations,
            )
        )

        patterns.extend(
            self._detect_shared_device_patterns(
                entities,
                relations,
            )
        )

        patterns.extend(
            self._detect_shared_location_patterns(
                entities,
                relations,
            )
        )

        patterns.extend(
            self._detect_case_patterns(
                entities,
                relations,
            )
        )

        patterns = self._remove_duplicates(
            patterns
        )

        return PatternRecognitionResult(
            patterns=patterns,
            metadata={
                "recognizer": "PatternRecognizer",
                "repeated_threshold": (
                    self.repeated_threshold
                ),
            },
        )

    # ========================================================
    # REPEATED ENTITIES
    # ========================================================

    def _detect_repeated_entities(
        self,
        entities: list[EntityCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect entities appearing multiple times.
        """

        groups: dict[
            tuple[str, str],
            list[EntityCandidate],
        ] = defaultdict(list)

        for entity in entities:

            key = (
                entity.entity_type,
                (
                    entity.normalized_value
                    or entity.value.lower()
                ),
            )

            groups[key].append(entity)

        patterns: list[
            PatternCandidate
        ] = []

        for (
            entity_type,
            normalized_value,
        ), matches in groups.items():

            count = len(matches)

            if count < self.repeated_threshold:
                continue

            representative = matches[0]

            if entity_type == "PERSON":
                pattern_type = REPEATED_PERSON

            elif entity_type == "PHONE":
                pattern_type = REPEATED_PHONE

            elif entity_type == "DEVICE":
                pattern_type = REPEATED_DEVICE

            elif entity_type == "LOCATION":
                pattern_type = REPEATED_LOCATION

            else:
                pattern_type = REPEATED_ENTITY

            patterns.append(
                PatternCandidate(
                    pattern_type=pattern_type,
                    description=(
                        f"{entity_type} "
                        f"'{representative.value}' "
                        f"appears {count} times."
                    ),
                    entities=matches,
                    confidence=min(
                        1.0,
                        0.60
                        + (0.10 * count),
                    ),
                    occurrences=count,
                    metadata={
                        "entity_type": entity_type,
                        "normalized_value": (
                            normalized_value
                        ),
                    },
                )
            )

        return patterns

    # ========================================================
    # RELATIONSHIP PATTERNS
    # ========================================================

    def _detect_relationship_patterns(
        self,
        relations: list[RelationCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect recurring relationships.
        """

        groups: dict[
            tuple[str, str, str],
            list[RelationCandidate],
        ] = defaultdict(list)

        for relation in relations:

            source = relation.source_entity

            target = relation.target_entity

            source_key = (
                source.normalized_value
                or source.value.lower()
            )

            target_key = (
                target.normalized_value
                or target.value.lower()
            )

            key = (
                relation.relation_type,
                source_key,
                target_key,
            )

            groups[key].append(
                relation
            )

        patterns: list[
            PatternCandidate
        ] = []

        for (
            relation_type,
            _source_key,
            _target_key,
        ), matches in groups.items():

            if len(matches) < self.repeated_threshold:
                continue

            first = matches[0]

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        RECURRING_RELATIONSHIP
                    ),
                    description=(
                        f"Relationship "
                        f"'{relation_type}' "
                        f"recurs {len(matches)} times "
                        f"between the same entities."
                    ),
                    entities=[
                        first.source_entity,
                        first.target_entity,
                    ],
                    relations=matches,
                    confidence=min(
                        1.0,
                        0.65
                        + (
                            0.08
                            * len(matches)
                        ),
                    ),
                    occurrences=len(matches),
                    evidence=[
                        relation.evidence_text
                        for relation in matches
                        if relation.evidence_text
                    ],
                )
            )

        return patterns

    # ========================================================
    # SHARED PHONE
    # ========================================================

    def _detect_shared_phone_patterns(
        self,
        entities: list[EntityCandidate],
        relations: list[RelationCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect multiple people associated with the same phone.
        """

        phone_to_people: dict[
            str,
            list[EntityCandidate],
        ] = defaultdict(list)

        for relation in relations:

            if (
                relation.relation_type
                != "PERSON_USED_PHONE"
            ):
                continue

            person = relation.source_entity
            phone = relation.target_entity

            if (
                person.entity_type != "PERSON"
                or phone.entity_type != "PHONE"
            ):
                continue

            phone_key = (
                phone.normalized_value
                or phone.value.lower()
            )

            phone_to_people[
                phone_key
            ].append(person)

        patterns: list[
            PatternCandidate
        ] = []

        for phone_key, people in (
            phone_to_people.items()
        ):

            unique_people = (
                self._unique_entities(
                    people
                )
            )

            if len(unique_people) < 2:
                continue

            phone = self._find_entity(
                entities,
                "PHONE",
                phone_key,
            )

            if phone is None:
                continue

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        MULTIPLE_PERSONS_SHARED_PHONE
                    ),
                    description=(
                        f"{len(unique_people)} "
                        f"distinct person candidates "
                        f"are associated with the same "
                        f"phone number."
                    ),
                    entities=[
                        phone,
                        *unique_people,
                    ],
                    relations=[
                        relation
                        for relation in relations
                        if (
                            relation.relation_type
                            == "PERSON_USED_PHONE"
                            and self._same_entity(
                                relation.target_entity,
                                phone,
                            )
                        )
                    ],
                    confidence=0.82,
                    occurrences=len(
                        unique_people
                    ),
                    metadata={
                        "phone": phone.value,
                        "person_count": len(
                            unique_people
                        ),
                    },
                )
            )

        return patterns

    # ========================================================
    # SHARED DEVICE
    # ========================================================

    def _detect_shared_device_patterns(
        self,
        entities: list[EntityCandidate],
        relations: list[RelationCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect multiple people associated with one device.
        """

        device_to_people: dict[
            str,
            list[EntityCandidate],
        ] = defaultdict(list)

        for relation in relations:

            if (
                relation.relation_type
                != "PERSON_USED_DEVICE"
            ):
                continue

            person = relation.source_entity
            device = relation.target_entity

            if (
                person.entity_type != "PERSON"
                or device.entity_type != "DEVICE"
            ):
                continue

            key = (
                device.normalized_value
                or device.value.lower()
            )

            device_to_people[
                key
            ].append(person)

        patterns: list[
            PatternCandidate
        ] = []

        for device_key, people in (
            device_to_people.items()
        ):

            unique_people = (
                self._unique_entities(
                    people
                )
            )

            if len(unique_people) < 2:
                continue

            device = self._find_entity(
                entities,
                "DEVICE",
                device_key,
            )

            if device is None:
                continue

            related = [
                relation
                for relation in relations
                if (
                    relation.relation_type
                    == "PERSON_USED_DEVICE"
                    and self._same_entity(
                        relation.target_entity,
                        device,
                    )
                )
            ]

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        MULTIPLE_PERSONS_SHARED_DEVICE
                    ),
                    description=(
                        f"{len(unique_people)} "
                        f"distinct person candidates "
                        f"are associated with the same "
                        f"device."
                    ),
                    entities=[
                        device,
                        *unique_people,
                    ],
                    relations=related,
                    confidence=0.82,
                    occurrences=len(
                        unique_people
                    ),
                    metadata={
                        "device": device.value,
                        "person_count": len(
                            unique_people
                        ),
                    },
                )
            )

        return patterns

    # ========================================================
    # SHARED LOCATION
    # ========================================================

    def _detect_shared_location_patterns(
        self,
        entities: list[EntityCandidate],
        relations: list[RelationCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect multiple people associated with the same location.
        """

        location_to_people: dict[
            str,
            list[EntityCandidate],
        ] = defaultdict(list)

        for relation in relations:

            if (
                relation.relation_type
                != "PERSON_AT_LOCATION"
            ):
                continue

            person = relation.source_entity
            location = relation.target_entity

            if (
                person.entity_type != "PERSON"
                or location.entity_type
                != "LOCATION"
            ):
                continue

            key = (
                location.normalized_value
                or location.value.lower()
            )

            location_to_people[
                key
            ].append(person)

        patterns: list[
            PatternCandidate
        ] = []

        for location_key, people in (
            location_to_people.items()
        ):

            unique_people = (
                self._unique_entities(
                    people
                )
            )

            if len(unique_people) < 2:
                continue

            location = self._find_entity(
                entities,
                "LOCATION",
                location_key,
            )

            if location is None:
                continue

            related = [
                relation
                for relation in relations
                if (
                    relation.relation_type
                    == "PERSON_AT_LOCATION"
                    and self._same_entity(
                        relation.target_entity,
                        location,
                    )
                )
            ]

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        MULTIPLE_PERSONS_SHARED_LOCATION
                    ),
                    description=(
                        f"{len(unique_people)} "
                        f"distinct person candidates "
                        f"are associated with the same "
                        f"location."
                    ),
                    entities=[
                        location,
                        *unique_people,
                    ],
                    relations=related,
                    confidence=0.72,
                    occurrences=len(
                        unique_people
                    ),
                    metadata={
                        "location": location.value,
                        "person_count": len(
                            unique_people
                        ),
                    },
                )
            )

        return patterns

    # ========================================================
    # CASE PATTERNS
    # ========================================================

    def _detect_case_patterns(
        self,
        entities: list[EntityCandidate],
        relations: list[RelationCandidate],
    ) -> list[PatternCandidate]:
        """
        Detect useful case/evidence/person patterns.
        """

        patterns: list[
            PatternCandidate
        ] = []

        # ----------------------------------------------------
        # Case + Evidence
        # ----------------------------------------------------

        evidence_relations = [
            relation
            for relation in relations
            if (
                relation.relation_type
                == "EVIDENCE_RELATED_CASE"
            )
        ]

        grouped_cases: dict[
            str,
            list[RelationCandidate],
        ] = defaultdict(list)

        for relation in evidence_relations:

            case = relation.target_entity

            case_key = (
                case.normalized_value
                or case.value.lower()
            )

            grouped_cases[
                case_key
            ].append(relation)

        for case_key, matches in (
            grouped_cases.items()
        ):

            if not matches:
                continue

            case = matches[0].target_entity

            evidence = [
                relation.source_entity
                for relation in matches
            ]

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        CASE_EVIDENCE_PATTERN
                    ),
                    description=(
                        f"Case '{case.value}' "
                        f"is associated with "
                        f"{len(evidence)} "
                        f"evidence candidate(s)."
                    ),
                    entities=[
                        case,
                        *evidence,
                    ],
                    relations=matches,
                    confidence=0.90,
                    occurrences=len(
                        evidence
                    ),
                )
            )

        # ----------------------------------------------------
        # Case + Person
        # ----------------------------------------------------

        person_relations = [
            relation
            for relation in relations
            if (
                relation.relation_type
                == "PERSON_IN_CASE"
            )
        ]

        grouped_people: dict[
            str,
            list[RelationCandidate],
        ] = defaultdict(list)

        for relation in person_relations:

            case = relation.target_entity

            key = (
                case.normalized_value
                or case.value.lower()
            )

            grouped_people[
                key
            ].append(relation)

        for case_key, matches in (
            grouped_people.items()
        ):

            if not matches:
                continue

            case = matches[0].target_entity

            people = [
                relation.source_entity
                for relation in matches
            ]

            patterns.append(
                PatternCandidate(
                    pattern_type=(
                        CASE_PERSON_PATTERN
                    ),
                    description=(
                        f"Case '{case.value}' "
                        f"is associated with "
                        f"{len(people)} "
                        f"person candidate(s)."
                    ),
                    entities=[
                        case,
                        *people,
                    ],
                    relations=matches,
                    confidence=0.85,
                    occurrences=len(
                        people
                    ),
                )
            )

        return patterns

    # ========================================================
    # FIND ENTITY
    # ========================================================

    @staticmethod
    def _find_entity(
        entities: list[EntityCandidate],
        entity_type: str,
        normalized_value: str,
    ) -> EntityCandidate | None:
        """
        Find an entity by type and normalized value.
        """

        for entity in entities:

            if (
                entity.entity_type
                != entity_type
            ):
                continue

            value = (
                entity.normalized_value
                or entity.value.lower()
            )

            if value == normalized_value:
                return entity

        return None

    # ========================================================
    # UNIQUE ENTITIES
    # ========================================================

    @staticmethod
    def _unique_entities(
        entities: Iterable[EntityCandidate],
    ) -> list[EntityCandidate]:
        """
        Remove duplicate entity candidates.
        """

        result: list[
            EntityCandidate
        ] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for entity in entities:

            key = (
                entity.entity_type,
                (
                    entity.normalized_value
                    or entity.value.lower()
                ),
            )

            if key in seen:
                continue

            seen.add(key)

            result.append(entity)

        return result

    # ========================================================
    # SAME ENTITY
    # ========================================================

    @staticmethod
    def _same_entity(
        first: EntityCandidate,
        second: EntityCandidate,
    ) -> bool:
        """
        Compare entity candidates.
        """

        if first is second:
            return True

        return (
            first.entity_type
            == second.entity_type
            and (
                first.normalized_value
                or first.value.lower()
            )
            == (
                second.normalized_value
                or second.value.lower()
            )
        )

    # ========================================================
    # DUPLICATES
    # ========================================================

    @staticmethod
    def _remove_duplicates(
        patterns: Iterable[PatternCandidate],
    ) -> list[PatternCandidate]:
        """
        Remove duplicate patterns.
        """

        result: list[
            PatternCandidate
        ] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for pattern in patterns:

            entity_keys = sorted(
                (
                    entity.entity_type,
                    (
                        entity.normalized_value
                        or entity.value.lower()
                    ),
                )
                for entity in pattern.entities
            )

            key = (
                pattern.pattern_type,
                str(entity_keys),
            )

            if key in seen:
                continue

            seen.add(key)

            result.append(pattern)

        return result


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def recognize_patterns(
    entities: Iterable[EntityCandidate],
    relations: Iterable[RelationCandidate] = (),
) -> PatternRecognitionResult:
    """
    Convenience function for pattern recognition.
    """

    recognizer = PatternRecognizer()

    return recognizer.recognize(
        entities=entities,
        relations=relations,
    )
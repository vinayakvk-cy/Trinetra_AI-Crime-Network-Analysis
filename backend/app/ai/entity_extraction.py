from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ============================================================
# ENTITY TYPES
# ============================================================


class ExtractedEntityType(str, Enum):
    """
    Entity types that TRINETRA can identify from intelligence.
    """

    PERSON = "person"

    PHONE = "phone"

    EMAIL = "email"

    VEHICLE = "vehicle"

    LOCATION = "location"

    ORGANIZATION = "organization"

    ACCOUNT = "account"

    DATE = "date"

    UNKNOWN = "unknown"


# ============================================================
# EXTRACTED ENTITY
# ============================================================


@dataclass
class ExtractedEntity:
    """
    Represents an entity detected in raw intelligence.
    """

    entity_type: ExtractedEntityType

    value: str

    confidence: float

    start_position: int | None = None

    end_position: int | None = None

    source: str = "rule_based_extractor"


# ============================================================
# ENTITY EXTRACTOR
# ============================================================


class EntityExtractor:
    """
    Extract structured entities from intelligence text.

    Current implementation:
        Rule-based extraction using regular expressions.

    Future implementation:
        NLP / NER / LLM models can be plugged into this class.
    """

    def extract(
        self,
        text: str,
    ) -> list[ExtractedEntity]:
        """
        Extract all supported entity types from text.
        """

        if not isinstance(text, str):
            raise TypeError(
                "Text must be a string."
            )

        text = text.strip()

        if not text:
            return []

        entities: list[ExtractedEntity] = []

        entities.extend(
            self._extract_emails(text)
        )

        entities.extend(
            self._extract_phone_numbers(text)
        )

        entities.extend(
            self._extract_dates(text)
        )

        entities.extend(
            self._extract_accounts(text)
        )

        entities.extend(
            self._extract_vehicles(text)
        )

        return self._remove_duplicates(
            entities
        )

    # ========================================================
    # EMAIL
    # ========================================================

    def _extract_emails(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        )

        entities: list[ExtractedEntity] = []

        for match in pattern.finditer(text):

            entities.append(
                ExtractedEntity(
                    entity_type=ExtractedEntityType.EMAIL,
                    value=match.group(0),
                    confidence=0.99,
                    start_position=match.start(),
                    end_position=match.end(),
                )
            )

        return entities

    # ========================================================
    # PHONE
    # ========================================================

    def _extract_phone_numbers(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        pattern = re.compile(
            r"(?<!\d)"
            r"(?:\+91[\s-]?)?"
            r"[6-9]\d{9}"
            r"(?!\d)"
        )

        entities: list[ExtractedEntity] = []

        for match in pattern.finditer(text):

            value = re.sub(
                r"[\s-]",
                "",
                match.group(0),
            )

            entities.append(
                ExtractedEntity(
                    entity_type=ExtractedEntityType.PHONE,
                    value=value,
                    confidence=0.98,
                    start_position=match.start(),
                    end_position=match.end(),
                )
            )

        return entities

    # ========================================================
    # DATES
    # ========================================================

    def _extract_dates(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b\d{1,2}\s+"
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{4}\b",
        ]

        entities: list[ExtractedEntity] = []

        for pattern in patterns:

            regex = re.compile(
                pattern,
                re.IGNORECASE,
            )

            for match in regex.finditer(text):

                entities.append(
                    ExtractedEntity(
                        entity_type=ExtractedEntityType.DATE,
                        value=match.group(0),
                        confidence=0.95,
                        start_position=match.start(),
                        end_position=match.end(),
                    )
                )

        return entities

    # ========================================================
    # ACCOUNT IDENTIFIERS
    # ========================================================

    def _extract_accounts(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        patterns = [
            r"\b(?:account|acct)[\s#:.-]*"
            r"[A-Za-z0-9_-]{4,30}\b",

            r"\b(?:upi|wallet)[\s#:.-]*"
            r"[A-Za-z0-9._@-]{4,50}\b",
        ]

        entities: list[ExtractedEntity] = []

        for pattern in patterns:

            regex = re.compile(
                pattern,
                re.IGNORECASE,
            )

            for match in regex.finditer(text):

                entities.append(
                    ExtractedEntity(
                        entity_type=ExtractedEntityType.ACCOUNT,
                        value=match.group(0),
                        confidence=0.85,
                        start_position=match.start(),
                        end_position=match.end(),
                    )
                )

        return entities

    # ========================================================
    # VEHICLE
    # ========================================================

    def _extract_vehicles(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        pattern = re.compile(
            r"\b[A-Z]{2}"
            r"[-\s]?"
            r"\d{1,2}"
            r"[-\s]?"
            r"[A-Z]{1,3}"
            r"[-\s]?"
            r"\d{1,4}\b",
            re.IGNORECASE,
        )

        entities: list[ExtractedEntity] = []

        for match in pattern.finditer(text):

            entities.append(
                ExtractedEntity(
                    entity_type=ExtractedEntityType.VEHICLE,
                    value=match.group(0).upper(),
                    confidence=0.92,
                    start_position=match.start(),
                    end_position=match.end(),
                )
            )

        return entities

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    def _remove_duplicates(
        self,
        entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:

        seen: set[
            tuple[
                ExtractedEntityType,
                str,
            ]
        ] = set()

        unique_entities: list[ExtractedEntity] = []

        for entity in entities:

            key = (
                entity.entity_type,
                entity.value.lower(),
            )

            if key in seen:
                continue

            seen.add(key)

            unique_entities.append(
                entity
            )

        return unique_entities


# ============================================================
# DEFAULT EXTRACTOR
# ============================================================


entity_extractor = EntityExtractor()
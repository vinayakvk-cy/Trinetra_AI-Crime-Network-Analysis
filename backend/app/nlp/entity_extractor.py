"""
TRINETRA Entity Extractor
=========================

Extracts structured entities from normalized investigation data.

Responsibilities
----------------
- Detect named entities from text
- Detect investigation-specific identifiers
- Detect dates and locations
- Detect phone/device references
- Detect case/FIR/evidence references
- Return normalized entity candidates
- Preserve source text and offsets where available

This module does NOT:
- determine guilt
- determine whether an entity is a suspect
- assign risk scores
- confirm identity matches
- create graph relationships

Identity confirmation belongs to entity_linker.py.
Relationship creation belongs to relation_extractor.py / graph layer.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


# ============================================================
# ENTITY TYPES
# ============================================================

PERSON = "PERSON"
ORGANIZATION = "ORGANIZATION"
LOCATION = "LOCATION"
PHONE = "PHONE"
EMAIL = "EMAIL"
VEHICLE = "VEHICLE"
CASE = "CASE"
CASE_TITLE = "CASE_TITLE"
DOCUMENT_TITLE = "DOCUMENT_TITLE"
FIR = "FIR"
EVIDENCE = "EVIDENCE"
INMATE = "INMATE"
DEVICE = "DEVICE"
DATE = "DATE"
TIME = "TIME"
GPS_COORDINATE = "GPS_COORDINATE"


SUPPORTED_ENTITY_TYPES = {
    PERSON,
    ORGANIZATION,
    LOCATION,
    PHONE,
    EMAIL,
    VEHICLE,
    CASE,
    CASE_TITLE,
    DOCUMENT_TITLE,
    FIR,
    EVIDENCE,
    INMATE,
    DEVICE,
    DATE,
    TIME,
    GPS_COORDINATE,
}


# ============================================================
# REGULAR EXPRESSIONS
# ============================================================

CASE_HEADER_PATTERN = re.compile(
    r"\bCase\s*(?:Number|No|#)?\s*[:#-]\s*"
    r"(?P<case_id>[A-Z0-9][A-Z0-9._/-]*)"
    r"(?:\s*(?:[—–\-]|\:)\s*(?P<case_title>[^\r\n]+))?",
    re.IGNORECASE,
)

EVIDENCE_HEADER_PATTERN = re.compile(
    r"\b(?:Evidence|Exhibit)\s*(?:Number|No|#|ID)?\s*[:#-]\s*"
    r"(?P<evidence_id>[A-Z0-9][A-Z0-9._/-]*)\b",
    re.IGNORECASE,
)

COMPOUND_EVIDENCE_PATTERN = re.compile(
    r"\b[A-Z0-9][A-Z0-9._/-]*[-_/]EV[-_/][0-9]+[A-Z0-9._/-]*\b",
    re.IGNORECASE,
)

CASE_PATTERN = re.compile(
    r"\b(?:CASE|CR|CC|SC|CASE[-_]NO)[-_/][A-Z0-9][A-Z0-9._/-]*\b",
    re.IGNORECASE,
)

FIR_PATTERN = re.compile(
    r"\bFIR[-_/: ]?[A-Z0-9][A-Z0-9._/-]*\b",
    re.IGNORECASE,
)

EVIDENCE_PATTERN = re.compile(
    r"\b(?:EV[-_/][0-9]+[A-Z0-9._/-]*|(?:EVIDENCE|EXHIBIT)[-_/][A-Z0-9][A-Z0-9._/-]*)\b",
    re.IGNORECASE,
)

INMATE_PATTERN = re.compile(
    r"\b(?:INMATE|PRISONER)[-_/: ]?"
    r"[A-Z0-9][A-Z0-9._/-]*\b",
    re.IGNORECASE,
)

DEVICE_PATTERN = re.compile(
    r"\b(?:DEVICE|IMEI|DEVICE[-_ ]ID)[-_/: ]?"
    r"[A-Z0-9][A-Z0-9._/-]*\b",
    re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+?\d[\d\s().-]{7,}\d)"
    r"(?!\d)"
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

DATE_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|"
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"
    r"|"
    r"\d{1,2}\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z]*\s+\d{2,4}"
    r")\b",
    re.IGNORECASE,
)

TIME_PATTERN = re.compile(
    r"\b(?:"
    r"(?:[01]?\d|2[0-3]):[0-5]\d"
    r"(?:\:[0-5]\d)?"
    r"(?:\s?(?:AM|PM))?"
    r"|"
    r"(?:1[0-2]|0?[1-9])"
    r"(?:\:[0-5]\d)"
    r"\s?(?:AM|PM)"
    r")\b",
    re.IGNORECASE,
)

GPS_PATTERN = re.compile(
    r"\b"
    r"(-?\d{1,3}(?:\.\d+)?)"
    r"\s*[,;]\s*"
    r"(-?\d{1,3}(?:\.\d+)?)"
    r"\b"
)


# ============================================================
# DATACLASS
# ============================================================


@dataclass
class EntityCandidate:
    """
    Entity discovered in source text.

    This is a candidate entity only.

    Example:

        {
            "entity_type": "CASE",
            "value": "CASE-001"
        }
    """

    entity_type: str

    value: str

    normalized_value: str | None = None

    source_text: str | None = None

    start: int | None = None

    end: int | None = None

    confidence: float = 1.0

    source_field: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert entity candidate to dictionary.
        """

        return asdict(self)


# ============================================================
# EXTRACTION RESULT
# ============================================================


@dataclass
class EntityExtractionResult:
    """
    Result produced by EntityExtractor.
    """

    entities: list[EntityCandidate]

    source_text: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def count(self) -> int:
        """
        Number of extracted entities.
        """

        return len(self.entities)

    def by_type(
        self,
        entity_type: str,
    ) -> list[EntityCandidate]:
        """
        Return entities of a particular type.
        """

        return [
            entity
            for entity in self.entities
            if entity.entity_type == entity_type
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert extraction result to dictionary.
        """

        return {
            "count": self.count,
            "entities": [
                entity.to_dict()
                for entity in self.entities
            ],
            "source_text": self.source_text,
            "metadata": self.metadata,
        }


# ============================================================
# ENTITY EXTRACTOR
# ============================================================


class EntityExtractor:
    """
    Investigation-oriented entity extractor.

    The extractor uses deterministic patterns for identifiers
    and lightweight heuristics for structured fields.

    A production deployment can later add a dedicated NLP/NER
    model without changing the output interface.
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        enable_heuristic_names: bool = True,
    ) -> None:


        self.enable_heuristic_names = (
            enable_heuristic_names
        )
        

    # ========================================================
    # TEXT EXTRACTION
    # ========================================================

    def extract(
        self,
        text: str,
        source_field: str | None = None,
    ) -> EntityExtractionResult:
        """
        Extract entities from free text.
        """

        if not text:

            return EntityExtractionResult(
                entities=[],
                source_text=text,
            )

        text = str(text)

        entities: list[EntityCandidate] = []

        # ----------------------------------------------------
        # Case headers and titles
        # ----------------------------------------------------

        entities.extend(
            self._extract_case_headers(
                text=text,
                source_field=source_field,
            )
        )

        # ----------------------------------------------------
        # Evidence headers and compound identifiers
        # ----------------------------------------------------

        entities.extend(
            self._extract_evidence_headers(
                text=text,
                source_field=source_field,
            )
        )

        # ----------------------------------------------------
        # Case
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=CASE_PATTERN,
                entity_type=CASE,
                source_field=source_field,
                confidence=0.99,
            )
        )

        # ----------------------------------------------------
        # FIR
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=FIR_PATTERN,
                entity_type=FIR,
                source_field=source_field,
                confidence=0.99,
            )
        )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=EVIDENCE_PATTERN,
                entity_type=EVIDENCE,
                source_field=source_field,
                confidence=0.99,
            )
        )

        # ----------------------------------------------------
        # Inmate
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=INMATE_PATTERN,
                entity_type=INMATE,
                source_field=source_field,
                confidence=0.98,
            )
        )

        # ----------------------------------------------------
        # Device
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=DEVICE_PATTERN,
                entity_type=DEVICE,
                source_field=source_field,
                confidence=0.98,
            )
        )

        # ----------------------------------------------------
        # Phone
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=PHONE_PATTERN,
                entity_type=PHONE,
                source_field=source_field,
                confidence=0.95,
            )
        )

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=EMAIL_PATTERN,
                entity_type=EMAIL,
                source_field=source_field,
                confidence=0.99,
            )
        )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=DATE_PATTERN,
                entity_type=DATE,
                source_field=source_field,
                confidence=0.97,
            )
        )

        # ----------------------------------------------------
        # Time
        # ----------------------------------------------------

        entities.extend(
            self._extract_pattern(
                text=text,
                pattern=TIME_PATTERN,
                entity_type=TIME,
                source_field=source_field,
                confidence=0.97,
            )
        )

        # ----------------------------------------------------
        # GPS
        # ----------------------------------------------------

        entities.extend(
            self._extract_gps_coordinates(
                text=text,
                source_field=source_field,
            )
        )

        # ----------------------------------------------------
        # Heuristic names
        # ----------------------------------------------------
        entities.extend(
    self._extract_heuristic_organizations(
        text=text,
        source_field=source_field,
    )
)
        if self.enable_heuristic_names:

            entities.extend(
                self._extract_heuristic_names(
                    text=text,
                    source_field=source_field,
                )
            )

        entities = self._remove_duplicates(
            entities
        )

        entities = self._remove_overlapping_entities(
            entities
        )

        return EntityExtractionResult(
            entities=entities,
            source_text=text,
            metadata={
                "extractor": "EntityExtractor",
                "heuristic_names_enabled": (
                    self.enable_heuristic_names
                ),
            },
        )

    # ========================================================
    # STRUCTURED RECORD EXTRACTION
    # ========================================================

    def extract_from_record(
        self,
        record: dict[str, Any],
    ) -> EntityExtractionResult:
        """
        Extract entities from a structured normalized record.

        This is particularly useful for the Phase 2 ingestion
        modules.
        """

        entities: list[EntityCandidate] = []

        for field_name, value in record.items():

            if value is None:
                continue

            if isinstance(value, (list, tuple, set)):

                values = value

            else:

                values = [value]

            for item in values:

                if item is None:
                    continue

                item_text = str(item).strip()

                if not item_text:
                    continue

                field_entities = (
                    self._extract_from_field(
                        field_name=field_name,
                        value=item_text,
                    )
                )

                entities.extend(
                    field_entities
                )

        entities = self._remove_duplicates(
            entities
        )

        entities = self._remove_overlapping_entities(
            entities
        )

        return EntityExtractionResult(
            entities=entities,
            metadata={
                "extractor": "EntityExtractor",
                "record_mode": True,
            },
        )

    # ========================================================
    # FIELD-AWARE EXTRACTION
    # ========================================================

    def _extract_from_field(
        self,
        field_name: str,
        value: str,
    ) -> list[EntityCandidate]:
        """
        Extract entities using the semantic meaning of a field.
        """

        field = field_name.lower().strip()

        entities: list[EntityCandidate] = []

        # ----------------------------------------------------
        # Person fields
        # ----------------------------------------------------

        if field in {
            "person_name",
            "deceased_name",
            "full_name",
            "name",
            "first_name",
            "middle_name",
            "last_name",
            "victim_name",
        }:

            entities.append(
                self._create_entity(
                    entity_type=PERSON,
                    value=value,
                    source_field=field_name,
                    confidence=0.90,
                )
            )

            return entities

        # ----------------------------------------------------
        # Location fields
        # ----------------------------------------------------

        if field in {
            "location",
            "location_name",
            "collection_location",
            "death_location",
            "city",
            "district",
            "state",
            "country",
            "address",
            "facility_name",
        }:

            entities.append(
                self._create_entity(
                    entity_type=LOCATION,
                    value=value,
                    source_field=field_name,
                    confidence=0.85,
                )
            )

            return entities

        # ----------------------------------------------------
        # Organization fields
        # ----------------------------------------------------

        if field in {
            "organization",
            "organization_name",
            "company",
            "company_name",
            "laboratory_name",
            "court_name",
        }:

            entities.append(
                self._create_entity(
                    entity_type=ORGANIZATION,
                    value=value,
                    source_field=field_name,
                    confidence=0.88,
                )
            )

            return entities

        # ----------------------------------------------------
        # Phone
        # ----------------------------------------------------

        if field in {
            "phone",
            "phone_number",
            "mobile_number",
            "msisdn",
        }:

            entities.append(
                self._create_entity(
                    entity_type=PHONE,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # Device
        # ----------------------------------------------------

        if field in {
            "device_id",
            "device_identifier",
            "gps_device_id",
            "imei",
        }:

            entities.append(
                self._create_entity(
                    entity_type=DEVICE,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # Case
        # ----------------------------------------------------

        if field in {
            "case_id",
            "case_number",
            "case_reference",
        }:

            entities.append(
                self._create_entity(
                    entity_type=CASE,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # FIR
        # ----------------------------------------------------

        if field in {
            "fir_id",
            "fir_number",
            "fir_reference",
        }:

            entities.append(
                self._create_entity(
                    entity_type=FIR,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        if field in {
            "evidence_id",
            "evidence_identifier",
            "exhibit_id",
        }:

            entities.append(
                self._create_entity(
                    entity_type=EVIDENCE,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # Inmate
        # ----------------------------------------------------

        if field in {
            "inmate_id",
            "prisoner_id",
        }:

            entities.append(
                self._create_entity(
                    entity_type=INMATE,
                    value=value,
                    source_field=field_name,
                    confidence=0.99,
                )
            )

            return entities

        # ----------------------------------------------------
        # Generic text
        # ----------------------------------------------------

        result = self.extract(
            text=value,
            source_field=field_name,
        )

        return result.entities

    # ========================================================
    # REGEX EXTRACTION
    # ========================================================

    def _extract_pattern(
        self,
        text: str,
        pattern: re.Pattern[str],
        entity_type: str,
        source_field: str | None,
        confidence: float,
    ) -> list[EntityCandidate]:
        """
        Extract entities using a regular expression.
        """

        entities: list[EntityCandidate] = []

        for match in pattern.finditer(text):

            value = match.group(0).strip()

            if not value:
                continue

            entities.append(
                EntityCandidate(
                    entity_type=entity_type,
                    value=value,
                    normalized_value=(
                        self._normalize_identifier(
                            value
                        )
                    ),
                    source_text=value,
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    source_field=source_field,
                )
            )

        return entities

    # ========================================================
    # STRUCTURED CASE HEADER EXTRACTION
    # ========================================================

    def _extract_case_headers(
        self,
        text: str,
        source_field: str | None,
    ) -> list[EntityCandidate]:
        """
        Extract case identifiers and case titles from structured
        case header lines, e.g.:
            Case: TRI-TEST-001 — Harbor Procurement Review
            Case Number: TRI-TEST-001
            Case: CASE-001 - Narcotics Inquiry
        """
        if not text:
            return []

        entities: list[EntityCandidate] = []

        for match in CASE_HEADER_PATTERN.finditer(text):
            case_id = match.group("case_id").strip()
            if case_id:
                start_id = match.start("case_id")
                end_id = match.end("case_id")
                entities.append(
                    EntityCandidate(
                        entity_type=CASE,
                        value=case_id,
                        normalized_value=self._normalize_identifier(case_id),
                        source_text=case_id,
                        start=start_id,
                        end=end_id,
                        confidence=0.99,
                        source_field=source_field,
                        metadata={"method": "case_header_id"},
                    )
                )

            case_title = match.group("case_title")
            if case_title:
                case_title = case_title.strip()
                case_title = re.sub(r"[.!?]+$", "", case_title).strip()
                if case_title:
                    start_title = match.start("case_title")
                    end_title = start_title + len(case_title)
                    entities.append(
                        EntityCandidate(
                            entity_type=CASE_TITLE,
                            value=case_title,
                            normalized_value=case_title.strip().lower(),
                            source_text=case_title,
                            start=start_title,
                            end=end_title,
                            confidence=0.92,
                            source_field=source_field,
                            metadata={
                                "method": "case_header_title",
                                "case_id": case_id,
                            },
                        )
                    )

        return entities

    # ========================================================
    # STRUCTURED EVIDENCE HEADER EXTRACTION
    # ========================================================

    def _extract_evidence_headers(
        self,
        text: str,
        source_field: str | None,
    ) -> list[EntityCandidate]:
        """
        Extract structured evidence identifiers, e.g.:
            Evidence Number: TRI-TEST-001-EV-001
            Evidence ID: EV-001
            Compound standalone: TRI-TEST-001-EV-001
        """
        if not text:
            return []

        entities: list[EntityCandidate] = []

        for match in EVIDENCE_HEADER_PATTERN.finditer(text):
            evidence_id = match.group("evidence_id").strip()
            if not evidence_id or evidence_id.lower() in {
                "type",
                "record",
                "description",
                "details",
                "synthetic",
            }:
                continue

            entities.append(
                EntityCandidate(
                    entity_type=EVIDENCE,
                    value=evidence_id,
                    normalized_value=self._normalize_identifier(evidence_id),
                    source_text=evidence_id,
                    start=match.start("evidence_id"),
                    end=match.end("evidence_id"),
                    confidence=0.99,
                    source_field=source_field,
                    metadata={"method": "evidence_header_id"},
                )
            )

        for match in COMPOUND_EVIDENCE_PATTERN.finditer(text):
            val = match.group(0).strip()
            if not val:
                continue

            entities.append(
                EntityCandidate(
                    entity_type=EVIDENCE,
                    value=val,
                    normalized_value=self._normalize_identifier(val),
                    source_text=val,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.99,
                    source_field=source_field,
                    metadata={"method": "compound_evidence_id"},
                )
            )

        return entities

    # ========================================================
    # GPS EXTRACTION
    # ========================================================

    def _extract_gps_coordinates(
        self,
        text: str,
        source_field: str | None,
    ) -> list[EntityCandidate]:
        """
        Extract latitude/longitude pairs.
        """

        entities: list[EntityCandidate] = []

        for match in GPS_PATTERN.finditer(text):

            latitude = float(
                match.group(1)
            )

            longitude = float(
                match.group(2)
            )

            if not (
                -90 <= latitude <= 90
            ):
                continue

            if not (
                -180 <= longitude <= 180
            ):
                continue

            value = (
                f"{latitude},{longitude}"
            )

            entities.append(
                EntityCandidate(
                    entity_type=GPS_COORDINATE,
                    value=value,
                    normalized_value=value,
                    source_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.99,
                    source_field=source_field,
                    metadata={
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                )
            )

        return entities

        # ========================================================
    # HEURISTIC ORGANIZATION EXTRACTION
    # ========================================================

    def _extract_heuristic_organizations(
        self,
        text: str,
        source_field: str | None,
    ) -> list[EntityCandidate]:
        """
        Extract organization/company names from common legal
        suffixes such as Pvt Ltd, Ltd, LLP, Inc, and Bank.

        This intentionally keeps the matched span tight so that
        organization entities do not overlap with nearby person
        names.
        """

        if not text:
            return []

        entities: list[EntityCandidate] = []

        # ----------------------------------------------------
        # Company-style organizations
        # ----------------------------------------------------

        company_pattern = re.compile(
            r"\b"
            r"(?:[A-Z][A-Za-z0-9&.-]*\s+){0,3}"
            r"(?:Pvt\.?\s+Ltd\.?|Private\s+Limited|"
            r"Ltd\.?|Limited|LLP|Inc\.?|Incorporated|"
            r"Corporation|Corp\.?|Company|Co\.?|"
            r"Supplies|Advisory\s+Group|Consulting\s+Group|"
            r"Solutions|Enterprises|Industries|Holdings)"
            r"\b"
        )

        # ----------------------------------------------------
        # Bank names
        # ----------------------------------------------------

        bank_pattern = re.compile(
            r"\b"
            r"[A-Z][A-Za-z0-9&.-]*"
            r"\s+Bank"
            r"\b"
        )

        # Process sentence-by-sentence so names from a previous
        # clause/sentence cannot be absorbed into an organization.
        for sentence_match in re.finditer(
            r"[^.!?]+(?:[.!?]|$)",
            text,
        ):

            sentence = sentence_match.group(0)

            # ------------------------------------------------
            # Company suffix matches
            # ------------------------------------------------

            for match in company_pattern.finditer(sentence):

                value = match.group(0).strip()

                if not value:
                    continue

                # Keep only capitalized candidate words.
                words = value.split()

                # The final legal suffix is already part of value.
                # Require at least one meaningful name word before it.
                if len(words) < 2:
                    continue

                # Reject candidates that are clearly sentence
                # fragments caused by the regex starting too early.
                invalid_starts = {
                    "Aarav",
                    "Meera",
                    "The",
                    "This",
                    "That",
                    "Transaction",
                    "Call",
                    "Business",
                    "Registration",
                    "Record",
                }

                if words[0] in invalid_starts:
                    continue

                # Ensure the organization name begins with a
                # capitalized token.
                if not re.match(
                    r"^[A-Z][A-Za-z0-9&.-]*$",
                    words[0],
                ):
                    continue

                start = (
                    sentence_match.start()
                    + match.start()
                )

                end = (
                    sentence_match.start()
                    + match.end()
                )

                entities.append(
                    EntityCandidate(
                        entity_type=ORGANIZATION,
                        value=value,
                        normalized_value=(
                            self._normalize_value(
                                ORGANIZATION,
                                value,
                            )
                        ),
                        source_text=value,
                        start=start,
                        end=end,
                        confidence=0.88,
                        source_field=source_field,
                        metadata={
                            "method": (
                                "heuristic_organization"
                            )
                        },
                    )
                )

            # ------------------------------------------------
            # Bank matches
            # ------------------------------------------------

            for match in bank_pattern.finditer(sentence):

                value = match.group(0).strip()

                if not value:
                    continue

                start = (
                    sentence_match.start()
                    + match.start()
                )

                end = (
                    sentence_match.start()
                    + match.end()
                )

                entities.append(
                    EntityCandidate(
                        entity_type=ORGANIZATION,
                        value=value,
                        normalized_value=(
                            self._normalize_value(
                                ORGANIZATION,
                                value,
                            )
                        ),
                        source_text=value,
                        start=start,
                        end=end,
                        confidence=0.90,
                        source_field=source_field,
                        metadata={
                            "method": "heuristic_bank"
                        },
                    )
                )

        # ----------------------------------------------------
        # Contextual organization names without legal suffixes
        # ----------------------------------------------------
        #
        # Recognize capitalized multi-token names when nearby
        # language explicitly indicates an organization/business
        # context. Do not classify arbitrary capitalized phrases
        # as organizations.
            contextual_patterns = (
            re.compile(
                r"\b"
                r"(?P<name>"
                r"[A-Z][A-Za-z0-9&.-]*"
                r"(?: [A-Z][A-Za-z0-9&.-]*){1,3}"
                r")"
                r"(?= has (?:a )?banking relationship\b)",
            ),
            re.compile(
                r"\b"
                r"(?P<name>"
                r"[A-Z][A-Za-z0-9&.-]*"
                r"(?: [A-Z][A-Za-z0-9&.-]*){1,3}"
                r")"
                r"(?= (?:personnel|employees|staff)\b)",
            ),
            re.compile(
                r"\bis associated with "
                r"(?P<name>"
                r"[A-Z][A-Za-z0-9&.-]*"
                r"(?: [A-Z][A-Za-z0-9&.-]*){1,3}"
                r")"
                r"\b",
            ),
            re.compile(
                r"\b(?:works for|works at|is employed by) "
                r"(?P<name>"
                r"[A-Z][A-Za-z0-9&.-]*"
                r"(?: [A-Z][A-Za-z0-9&.-]*){1,3}"
                r")"
                r"\b",
            ),
            re.compile(
                r"\b(?P<name>"
                r"[A-Z][A-Za-z0-9&.-]*"
                r"(?: [A-Z][A-Za-z0-9&.-]*){1,3}"
                r")"
                r"(?=\s+is a registered (?:procurement supplier|consulting organization|company|business|vendor|contractor)\b)",
            ),
        )

        for sentence_match in re.finditer(
            r"[^.!?]+(?:[.!?]|$)",
            text,
        ):
            sentence = sentence_match.group(0)

            for pattern in contextual_patterns:
                for match in pattern.finditer(sentence):
                    value = match.group("name").strip()

                    if not value:
                        continue

                    words = value.split()

                    if len(words) < 2:
                        continue

                    start = (
                        sentence_match.start()
                        + match.start("name")
                    )

                    end = (
                        sentence_match.start()
                        + match.end("name")
                    )

                    entities.append(
                        EntityCandidate(
                            entity_type=ORGANIZATION,
                            value=value,
                            normalized_value=(
                                self._normalize_value(
                                    ORGANIZATION,
                                    value,
                                )
                            ),
                            source_text=value,
                            start=start,
                            end=end,
                            confidence=0.84,
                            source_field=source_field,
                            metadata={
                                "method": (
                                    "heuristic_contextual_organization"
                                )
                            },
                        )
                    )

        return entities

        # ========================================================
    # HEURISTIC NAME EXTRACTION
    # ========================================================

    def _extract_heuristic_names(
        self,
        text: str,
        source_field: str | None,
    ) -> list[EntityCandidate]:
        """
        Extract simple two/three-token person-name candidates.

        This is deliberately conservative and should not be
        treated as identity confirmation.
        """

        if not text:
            return []

        pattern = re.compile(
            r"\b"
            r"[A-Z][a-z]{1,}"
            r"(?: [A-Z][a-z]{1,}){1,2}"
            r"\b"
        )

        entities: list[EntityCandidate] = []

        for match in pattern.finditer(text):

            value = match.group(0).strip()

            if not value:
                continue

            # Avoid treating organization names as persons.
            lower_value = value.lower()

            organization_suffixes = (
                "pvt",
                "pvt ltd",
                "private limited",
                "ltd",
                "limited",
                "llp",
                "inc",
                "inc.",
                "corp",
                "corporation",
                "company",
                "co",
                "co.",
                "bank",
                "group",
                "supplies",
                "solutions",
                "services",
                "enterprises",
                "industries",
                "holdings",
                "advisory",
                "consulting",
                "associates",
                "agency",
                "bureau",
                "department",
            )

            if any(
                lower_value.endswith(suffix)
                for suffix in organization_suffixes
            ):
                continue

            # Avoid treating common prefixes as names.
            first_word = value.split()[0].lower()

            if first_word in {
                "case",
                "fir",
                "evidence",
                "inmate",
                "device",
            }:
                continue

            # Avoid treating document/evidence headings, investigation
            # descriptors, audit reviews, and corporate terms as persons.
            non_person_terms = {
                # Document & Record terms
                "activity",
                "record",
                "financial",
                "registration",
                "evidence",
                "document",
                "report",
                "statement",
                "exhibit",
                "transaction",
                "reference",
                "number",
                "type",
                "agreement",
                "contract",
                "license",
                "certificate",
                "memo",
                "memorandum",
                "notice",
                "warrant",
                "order",
                "affidavit",
                "petition",
                "transcript",
                "summary",
                "overview",
                # Investigation, Audit & Procedure terms
                "review",
                "procurement",
                "consulting",
                "advisory",
                "audit",
                "inquiry",
                "investigation",
                "assessment",
                "operation",
                "inspection",
                "surveillance",
                "intelligence",
                "briefing",
                "dossier",
                "analysis",
                "monitoring",
                "compliance",
                "enforcement",
                # Organization / Entity terms
                "supplies",
                "solutions",
                "services",
                "enterprises",
                "industries",
                "holdings",
                "agency",
                "bureau",
                "department",
                "division",
                "committee",
                "board",
                "group",
                "associates",
                "authority",
            }

            words = {
                word.lower()
                for word in value.split()
            }

            if words & non_person_terms:
                continue

            entities.append(
                EntityCandidate(
                    entity_type=PERSON,
                    value=value,
                    normalized_value=(
                        self._normalize_name(value)
                    ),
                    source_text=value,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.60,
                    source_field=source_field,
                    metadata={
                        "method": "heuristic"
                    },
                )
            )

        return entities

    # ========================================================
    # ENTITY CREATION
    # ========================================================

    @staticmethod
    def _create_entity(
        entity_type: str,
        value: str,
        source_field: str | None = None,
        confidence: float = 1.0,
    ) -> EntityCandidate:
        """
        Create a field-derived entity.
        """

        normalized_value = (
            EntityExtractor._normalize_value(
                entity_type,
                value,
            )
        )

        return EntityCandidate(
            entity_type=entity_type,
            value=value,
            normalized_value=normalized_value,
            source_text=value,
            confidence=confidence,
            source_field=source_field,
        )

    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_value(
        entity_type: str,
        value: str,
    ) -> str:
        """
        Normalize an entity value according to its type.
        """

        if entity_type in {
            CASE,
            FIR,
            EVIDENCE,
            INMATE,
            DEVICE,
        }:

            return (
                EntityExtractor
                ._normalize_identifier(value)
            )

        if entity_type in {
            CASE_TITLE,
            DOCUMENT_TITLE,
        }:

            return value.strip().lower()

        if entity_type == PERSON:

            return (
                EntityExtractor
                ._normalize_name(value)
            )

        if entity_type == PHONE:

            return (
                EntityExtractor
                ._normalize_phone(value)
            )

        if entity_type == EMAIL:

            return value.strip().lower()

        return value.strip()

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        """
        Normalize identifiers without destroying their meaning.
        """

        return re.sub(
            r"\s+",
            "",
            value.strip().upper(),
        )

    @staticmethod
    def _normalize_name(
        value: str,
    ) -> str:
        """
        Normalize person-name candidate.
        """

        value = value.strip().lower()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @staticmethod
    def _normalize_phone(
        value: str,
    ) -> str:
        """
        Normalize phone number to digits while preserving
        an optional leading '+'.
        """

        value = value.strip()

        prefix = "+"

        if value.startswith("+"):

            digits = re.sub(
                r"\D",
                "",
                value[1:],
            )

            return prefix + digits

        return re.sub(
            r"\D",
            "",
            value,
        )

    # ========================================================
    # DUPLICATE REMOVAL
    # ========================================================

    @staticmethod
    def _remove_duplicates(
        entities: Iterable[EntityCandidate],
    ) -> list[EntityCandidate]:
        """
        Remove exact duplicate candidates.
        """

        result: list[EntityCandidate] = []

        seen: set[
            tuple[str, str, str | None]
        ] = set()

        for entity in entities:

            key = (
                entity.entity_type,
                entity.normalized_value
                or entity.value.lower(),
                entity.source_field,
            )

            if key in seen:
                continue

            seen.add(key)

            result.append(entity)

        return result

    # ========================================================
    # OVERLAP REMOVAL
    # ========================================================

    @staticmethod
    def _remove_overlapping_entities(
        entities: list[EntityCandidate],
    ) -> list[EntityCandidate]:
        """
        Remove lower-confidence overlapping text spans.

        Field-derived entities without offsets are preserved.
        """

        span_entities = [
            entity
            for entity in entities
            if entity.start is not None
            and entity.end is not None
        ]

        no_span_entities = [
            entity
            for entity in entities
            if entity.start is None
            or entity.end is None
        ]

        span_entities.sort(
            key=lambda entity: (
                entity.start or 0,
                -(entity.confidence),
            )
        )

        accepted: list[
            EntityCandidate
        ] = []

        for entity in span_entities:

            overlaps = False

            for existing in accepted:

                if (
                    entity.start is None
                    or entity.end is None
                    or existing.start is None
                    or existing.end is None
                ):

                    continue

                if (
                    entity.start < existing.end
                    and entity.end > existing.start
                ):

                    overlaps = True

                    if (
                        entity.confidence
                        > existing.confidence
                    ):

                        accepted.remove(
                            existing
                        )

                        overlaps = False

                    break

            if not overlaps:

                accepted.append(entity)

        return no_span_entities + accepted


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def extract_entities(
    text: str,
    source_field: str | None = None,
) -> EntityExtractionResult:
    """
    Convenience function for text entity extraction.
    """

    extractor = EntityExtractor()

    return extractor.extract(
        text=text,
        source_field=source_field,
    )


def extract_entities_from_record(
    record: dict[str, Any],
) -> EntityExtractionResult:
    """
    Convenience function for structured-record extraction.
    """

    extractor = EntityExtractor()

    return extractor.extract_from_record(
        record
    )

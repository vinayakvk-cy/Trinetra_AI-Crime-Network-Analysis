"""
TRINETRA FIR Ingestion
======================

FIR-specific ingestion and normalization.

This module converts generic parsed/normalized records into a
consistent FIR representation.

Responsibilities
----------------
- Identify FIR-related fields
- Normalize FIR records
- Preserve narrative text
- Extract structured FIR attributes
- Prepare entities for the NLP/entity-linking pipeline

This module DOES NOT:
- determine guilt
- classify a person as a criminal
- assign suspect probability
- make investigative decisions
- automatically link people solely by name

Those operations belong to later analytical stages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.ingestion.normalizer import DataNormalizer
from app.ingestion.validators import (
    RecordValidator,
    ValidationIssue,
)


# ============================================================
# FIR FIELD ALIASES
# ============================================================

FIR_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # FIR identification
    # --------------------------------------------------------

    "fir_no": "fir_number",
    "fir_number": "fir_number",
    "fir_id": "fir_number",
    "fir_registration_number": "fir_number",

    # --------------------------------------------------------
    # Case
    # --------------------------------------------------------

    "case_no": "case_number",
    "case_number": "case_number",
    "case_id": "case_number",

    # --------------------------------------------------------
    # Police information
    # --------------------------------------------------------

    "police_station_name": "police_station",
    "station_name": "police_station",
    "ps_name": "police_station",

    "police_station_code": "police_station_code",
    "station_code": "police_station_code",

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    "date_of_incident": "incident_date",
    "incident_datetime": "incident_date",
    "date_of_occurrence": "incident_date",

    "date_of_fir": "fir_date",
    "fir_registration_date": "fir_date",

    # --------------------------------------------------------
    # People
    # --------------------------------------------------------

    "complainant_name": "complainant",
    "complainant_person": "complainant",

    "victim_name": "victims",
    "victim": "victims",

    "accused_name": "accused",
    "accused_person": "accused",

    "suspect_name": "persons_of_interest",
    "suspect": "persons_of_interest",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "incident_location": "location",
    "place_of_occurrence": "location",
    "place_of_incident": "location",

    # --------------------------------------------------------
    # Offence
    # --------------------------------------------------------

    "crime_type": "offence",
    "offense": "offence",
    "offences": "offence",
    "sections": "legal_sections",
    "ipc_sections": "legal_sections",
    "law_sections": "legal_sections",

    # --------------------------------------------------------
    # Narrative
    # --------------------------------------------------------

    "description": "narrative",
    "incident_description": "narrative",
    "case_description": "narrative",
    "complaint": "narrative",
    "complaint_text": "narrative",
    "fir_text": "narrative",
    "narration": "narrative",
    "statement": "narrative",
}


# ============================================================
# FIR RECORD
# ============================================================


@dataclass
class FIRRecord:
    """
    Canonical internal representation of an FIR.

    The record is deliberately separated from the database
    model. This allows the ingestion layer to process external
    files without tightly coupling them to SQLAlchemy.
    """

    fir_number: str | None = None

    case_number: str | None = None

    fir_date: str | None = None

    incident_date: str | None = None

    police_station: str | None = None

    police_station_code: str | None = None

    location: str | None = None

    district: str | None = None

    state: str | None = None

    offence: str | None = None

    legal_sections: Any = None

    complainant: Any = None

    victims: Any = None

    accused: Any = None

    persons_of_interest: Any = None

    narrative: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # --------------------------------------------------------
    # NLP input
    # --------------------------------------------------------

    @property
    def nlp_text(self) -> str:
        """
        Return the text that should be passed to the NLP layer.

        Structured fields are included along with the FIR
        narrative so that the NLP pipeline has useful context.
        """

        parts: list[str] = []

        if self.narrative:
            parts.append(
                f"FIR Narrative: {self.narrative}"
            )

        if self.offence:
            parts.append(
                f"Offence: {self.offence}"
            )

        if self.location:
            parts.append(
                f"Location: {self.location}"
            )

        if self.complainant:
            parts.append(
                f"Complainant: {self.complainant}"
            )

        if self.victims:
            parts.append(
                f"Victims: {self.victims}"
            )

        if self.accused:
            parts.append(
                f"Accused: {self.accused}"
            )

        return "\n".join(parts)

    # --------------------------------------------------------
    # Dictionary conversion
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Convert FIRRecord into a dictionary.
        """

        return asdict(self)


# ============================================================
# FIR PROCESSOR
# ============================================================


class FIRProcessor:
    """
    FIR-specific ingestion processor.

    Typical usage:

        processor = FIRProcessor()

        result = processor.process_records(
            records
        )

        for fir in result.records:
            print(fir.to_dict())
    """

    def __init__(self) -> None:

        self.normalizer = DataNormalizer()

        self.validator = RecordValidator()

    # ========================================================
    # PROCESS MULTIPLE FIR RECORDS
    # ========================================================

    def process_records(
        self,
        records: Iterable[dict[str, Any]],
        source_file: str | None = None,
    ) -> FIRProcessingResult:
        """
        Process multiple FIR records.
        """

        records = list(records)

        processed: list[FIRRecord] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            # ------------------------------------------------
            # Normalize field names first
            # ------------------------------------------------

            normalized = self._normalize_fir_fields(
                record
            )

            # ------------------------------------------------
            # Validate normalized record
            # ------------------------------------------------

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            # ------------------------------------------------
            # Convert into FIRRecord
            # ------------------------------------------------

            fir = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(fir)

        return FIRProcessingResult(
            records=processed,
            validation_issues=validation_issues,
            source_file=source_file,
        )

    # ========================================================
    # PROCESS SINGLE FIR
    # ========================================================

    def process_record(
        self,
        record: dict[str, Any],
        source_file: str | None = None,
    ) -> FIRRecord:
        """
        Convert one generic record into a FIRRecord.
        """

        normalized = self._normalize_fir_fields(
            record
        )

        # ----------------------------------------------------
        # Extract standard fields
        # ----------------------------------------------------

        fir = FIRRecord(
            fir_number=self._get_string(
                normalized,
                "fir_number",
            ),

            case_number=self._get_string(
                normalized,
                "case_number",
            ),

            fir_date=self._get_string(
                normalized,
                "fir_date",
            ),

            incident_date=self._get_string(
                normalized,
                "incident_date",
            ),

            police_station=self._get_string(
                normalized,
                "police_station",
            ),

            police_station_code=self._get_string(
                normalized,
                "police_station_code",
            ),

            location=self._get_string(
                normalized,
                "location",
            ),

            district=self._get_string(
                normalized,
                "district",
            ),

            state=self._get_string(
                normalized,
                "state",
            ),

            offence=self._get_string(
                normalized,
                "offence",
            ),

            legal_sections=normalized.get(
                "legal_sections"
            ),

            complainant=normalized.get(
                "complainant"
            ),

            victims=normalized.get(
                "victims"
            ),

            accused=normalized.get(
                "accused"
            ),

            persons_of_interest=normalized.get(
                "persons_of_interest"
            ),

            narrative=self._get_string(
                normalized,
                "narrative",
            ),

            source_file=source_file,

            metadata={
                "source": "fir",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

        return fir

    # ========================================================
    # NORMALIZE FIR FIELDS
    # ========================================================

    def _normalize_fir_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert generic field names into FIR-specific
        canonical field names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            # First apply generic normalization.
            canonical_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            # Then apply FIR-specific aliases.
            fir_key = FIR_FIELD_ALIASES.get(
                canonical_key,
                canonical_key,
            )

            # Normalize the value using the generic
            # normalizer where possible.
            normalized_value = (
                self.normalizer.normalize_value(
                    fir_key,
                    value,
                )
            )

            # ------------------------------------------------
            # Preserve duplicate mapped values
            # ------------------------------------------------

            if fir_key in normalized:

                existing = normalized[fir_key]

                if existing in (None, ""):

                    normalized[fir_key] = (
                        normalized_value
                    )

                elif normalized_value in (
                    None,
                    "",
                ):

                    continue

                else:

                    # If multiple fields map to the same
                    # canonical field, preserve the additional
                    # value rather than silently deleting it.
                    alternate_key = (
                        f"{fir_key}_alternate"
                    )

                    normalized[
                        alternate_key
                    ] = normalized_value

            else:

                normalized[fir_key] = (
                    normalized_value
                )

        return normalized

    # ========================================================
    # STRING HELPER
    # ========================================================

    @staticmethod
    def _get_string(
        record: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Safely retrieve a field as a string.
        """

        value = record.get(key)

        if value is None:
            return None

        if isinstance(value, str):

            value = value.strip()

            return value or None

        return str(value)

    # ========================================================
    # REQUIRED FIELD CHECK
    # ========================================================

    @staticmethod
    def validate_minimum_fir_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify important FIR fields that are missing.

        Missing fields are reported rather than automatically
        rejecting the FIR because real-world records may be
        incomplete.
        """

        recommended_fields = (
            "fir_number",
            "case_number",
            "fir_date",
            "police_station",
            "location",
            "narrative",
        )

        missing: list[str] = []

        for field_name in recommended_fields:

            value = record.get(field_name)

            if value is None:
                missing.append(field_name)

            elif isinstance(value, str) and not value.strip():
                missing.append(field_name)

        return missing


# ============================================================
# PROCESSING RESULT
# ============================================================


@dataclass
class FIRProcessingResult:
    """
    Result returned after FIR processing.
    """

    records: list[FIRRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of FIR records processed.
        """

        return len(self.records)

    @property
    def has_validation_errors(self) -> bool:
        """
        Whether any error-level validation issues exist.
        """

        return any(
            issue.severity == "error"
            for issue in self.validation_issues
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert processing result into a serializable
        dictionary.
        """

        return {
            "source_file": self.source_file,
            "count": self.count,
            "has_validation_errors": (
                self.has_validation_errors
            ),
            "validation_issues": [
                {
                    "record_index": issue.record_index,
                    "field": issue.field,
                    "message": issue.message,
                    "severity": issue.severity,
                }
                for issue in self.validation_issues
            ],
            "records": [
                record.to_dict()
                for record in self.records
            ],
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_fir_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> FIRProcessingResult:
    """
    Convenience function for processing FIR records.

    Example:

        result = process_fir_records(
            records,
            source_file="fir_001.csv",
        )
    """

    processor = FIRProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
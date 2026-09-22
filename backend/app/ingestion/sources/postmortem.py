"""
TRINETRA Postmortem / Autopsy Ingestion
========================================

Postmortem-specific ingestion and normalization.

Responsibilities
----------------
- Normalize postmortem record identifiers
- Normalize deceased-person identifiers
- Normalize case/FIR references
- Normalize examination dates
- Preserve cause-of-death findings
- Preserve manner-of-death information when supplied
- Preserve injury findings
- Preserve toxicology information
- Preserve pathology information
- Preserve examiner information
- Preserve examination facility information
- Prepare records for entity linking
- Prepare records for graph construction

This module does NOT:
- independently determine cause of death
- infer homicide/suicide/accident from raw data
- determine criminal responsibility
- fabricate medical conclusions
- replace a qualified forensic pathologist
- alter the original forensic findings

Only authorized postmortem records should enter this pipeline.
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
# FIELD ALIASES
# ============================================================

POSTMORTEM_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Record identifiers
    # --------------------------------------------------------

    "record_id": "record_id",
    "postmortem_id": "record_id",
    "post_mortem_id": "record_id",
    "autopsy_id": "record_id",
    "autopsy_record_id": "record_id",
    "pm_number": "record_id",
    "pm_no": "record_id",

    # --------------------------------------------------------
    # Person / deceased identifiers
    # --------------------------------------------------------

    "person_id": "person_id",
    "person_identifier": "person_id",
    "individual_id": "person_id",
    "deceased_id": "person_id",
    "deceased_identifier": "person_id",

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    "name": "deceased_name",
    "full_name": "deceased_name",
    "deceased_name": "deceased_name",
    "victim_name": "deceased_name",

    "first_name": "first_name",
    "middle_name": "middle_name",
    "last_name": "last_name",
    "surname": "last_name",

    # --------------------------------------------------------
    # Case references
    # --------------------------------------------------------

    "case_id": "case_reference",
    "case_number": "case_reference",
    "case_no": "case_reference",
    "case_reference_number": "case_reference",

    "fir_id": "fir_reference",
    "fir_number": "fir_reference",
    "fir_no": "fir_reference",

    # --------------------------------------------------------
    # Examination information
    # --------------------------------------------------------

    "examination_date": "examination_timestamp",
    "postmortem_date": "examination_timestamp",
    "post_mortem_date": "examination_timestamp",
    "autopsy_date": "examination_timestamp",
    "examined_at": "examination_timestamp",

    "examination_time": "examination_timestamp",
    "postmortem_time": "examination_timestamp",
    "autopsy_time": "examination_timestamp",

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    "hospital": "facility_name",
    "hospital_name": "facility_name",
    "mortuary": "facility_name",
    "mortuary_name": "facility_name",
    "facility": "facility_name",
    "facility_name": "facility_name",

    "facility_id": "facility_id",
    "hospital_id": "facility_id",

    # --------------------------------------------------------
    # Examiner
    # --------------------------------------------------------

    "doctor": "examiner_name",
    "doctor_name": "examiner_name",
    "examiner": "examiner_name",
    "examiner_name": "examiner_name",
    "pathologist": "examiner_name",
    "pathologist_name": "examiner_name",

    "examiner_id": "examiner_id",
    "doctor_id": "examiner_id",

    # --------------------------------------------------------
    # Cause of death
    # --------------------------------------------------------

    "cause_of_death": "cause_of_death",
    "cause_death": "cause_of_death",
    "death_cause": "cause_of_death",

    # --------------------------------------------------------
    # Manner of death
    # --------------------------------------------------------

    "manner_of_death": "manner_of_death",
    "death_manner": "manner_of_death",
    "manner": "manner_of_death",

    # --------------------------------------------------------
    # Injury information
    # --------------------------------------------------------

    "injury": "injury_findings",
    "injuries": "injury_findings",
    "injury_findings": "injury_findings",
    "injury_description": "injury_findings",
    "wound_description": "injury_findings",

    # --------------------------------------------------------
    # Pathology
    # --------------------------------------------------------

    "pathology": "pathology_findings",
    "pathology_findings": "pathology_findings",
    "histopathology": "pathology_findings",
    "histopathology_findings": "pathology_findings",

    # --------------------------------------------------------
    # Toxicology
    # --------------------------------------------------------

    "toxicology": "toxicology_findings",
    "toxicology_result": "toxicology_findings",
    "toxicology_results": "toxicology_findings",
    "chemical_analysis": "toxicology_findings",

    # --------------------------------------------------------
    # Identification
    # --------------------------------------------------------

    "identification_status": "identification_status",
    "identified": "identification_status",
    "identity_status": "identification_status",

    # --------------------------------------------------------
    # Estimated time of death
    # --------------------------------------------------------

    "time_of_death": "estimated_time_of_death",
    "estimated_time_of_death": "estimated_time_of_death",
    "death_time": "estimated_time_of_death",

    # --------------------------------------------------------
    # Death location
    # --------------------------------------------------------

    "death_location": "death_location",
    "place_of_death": "death_location",
    "location_of_death": "death_location",

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    "status": "status",
    "report_status": "status",
    "postmortem_status": "status",

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    "source": "source_system",
    "data_source": "source_system",
    "source_system": "source_system",
}


# ============================================================
# POSTMORTEM RECORD
# ============================================================


@dataclass
class PostmortemRecord:
    """
    Canonical representation of a postmortem/autopsy record.

    This object belongs to the ingestion layer and is independent
    from database models.
    """

    record_id: str | None = None

    person_id: str | None = None

    deceased_name: str | None = None

    first_name: str | None = None

    middle_name: str | None = None

    last_name: str | None = None

    case_reference: str | None = None

    fir_reference: str | None = None

    examination_timestamp: str | None = None

    facility_id: str | None = None

    facility_name: str | None = None

    examiner_name: str | None = None

    examiner_id: str | None = None

    cause_of_death: str | None = None

    manner_of_death: str | None = None

    injury_findings: str | None = None

    pathology_findings: str | None = None

    toxicology_findings: str | None = None

    identification_status: str | None = None

    estimated_time_of_death: str | None = None

    death_location: str | None = None

    status: str | None = None

    source_system: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # RESOLVED NAME
    # ========================================================

    @property
    def resolved_name(self) -> str | None:
        """
        Return the best available representation of the deceased
        person's name.

        This is source data only and does not establish identity.
        """

        if self.deceased_name:
            return self.deceased_name

        parts = [
            self.first_name,
            self.middle_name,
            self.last_name,
        ]

        parts = [
            part.strip()
            for part in parts
            if part and part.strip()
        ]

        if not parts:
            return None

        return " ".join(parts)

    # ========================================================
    # GRAPH REPRESENTATION
    # ========================================================

    @property
    def graph_entity(self) -> dict[str, Any]:
        """
        Return a graph-oriented representation.

        The graph builder determines which relationships should
        actually be created.
        """

        return {
            "entity_type": "POSTMORTEM_RECORD",
            "record_id": self.record_id,
            "person_id": self.person_id,
            "deceased_name": self.resolved_name,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
            "examination_timestamp": (
                self.examination_timestamp
            ),
            "facility_id": self.facility_id,
            "facility_name": self.facility_name,
            "cause_of_death": self.cause_of_death,
            "manner_of_death": self.manner_of_death,
            "death_location": self.death_location,
        }

    # ========================================================
    # ENTITY LINKING CANDIDATE
    # ========================================================

    @property
    def entity_link_candidate(self) -> dict[str, Any]:
        """
        Return attributes that can be supplied to the entity
        linking layer.

        These are candidate attributes and must not be treated
        as confirmed identity matches automatically.
        """

        return {
            "person_id": self.person_id,
            "name": self.resolved_name,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
            "death_location": self.death_location,
            "estimated_time_of_death": (
                self.estimated_time_of_death
            ),
        }

    # ========================================================
    # NLP TEXT
    # ========================================================

    @property
    def nlp_text(self) -> str:
        """
        Return descriptive postmortem text for the NLP layer.
        """

        parts: list[str] = []

        if self.cause_of_death:
            parts.append(
                f"Cause of Death: "
                f"{self.cause_of_death}"
            )

        if self.manner_of_death:
            parts.append(
                f"Manner of Death: "
                f"{self.manner_of_death}"
            )

        if self.injury_findings:
            parts.append(
                f"Injury Findings: "
                f"{self.injury_findings}"
            )

        if self.pathology_findings:
            parts.append(
                f"Pathology Findings: "
                f"{self.pathology_findings}"
            )

        if self.toxicology_findings:
            parts.append(
                f"Toxicology Findings: "
                f"{self.toxicology_findings}"
            )

        if self.death_location:
            parts.append(
                f"Death Location: "
                f"{self.death_location}"
            )

        return "\n".join(parts)

    # ========================================================
    # DICTIONARY
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the record to a dictionary.
        """

        return asdict(self)


# ============================================================
# PROCESSING RESULT
# ============================================================


@dataclass
class PostmortemProcessingResult:
    """
    Result returned after processing postmortem records.
    """

    records: list[PostmortemRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of records processed.
        """

        return len(self.records)

    @property
    def has_validation_errors(self) -> bool:
        """
        Return True when an error-level validation issue exists.
        """

        return any(
            issue.severity == "error"
            for issue in self.validation_issues
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert processing result to a dictionary.
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
# POSTMORTEM PROCESSOR
# ============================================================


class PostmortemRecordProcessor:
    """
    Processes authorized postmortem/autopsy records into a
    canonical structure.
    """

    def __init__(self) -> None:

        self.normalizer = DataNormalizer()

        self.validator = RecordValidator()

    # ========================================================
    # MULTIPLE RECORDS
    # ========================================================

    def process_records(
        self,
        records: Iterable[dict[str, Any]],
        source_file: str | None = None,
    ) -> PostmortemProcessingResult:
        """
        Process multiple postmortem records.
        """

        records = list(records)

        processed: list[
            PostmortemRecord
        ] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_postmortem_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            postmortem_record = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(
                postmortem_record
            )

        return PostmortemProcessingResult(
            records=processed,
            validation_issues=validation_issues,
            source_file=source_file,
        )

    # ========================================================
    # SINGLE RECORD
    # ========================================================

    def process_record(
        self,
        record: dict[str, Any],
        source_file: str | None = None,
    ) -> PostmortemRecord:
        """
        Convert one generic record into a PostmortemRecord.
        """

        normalized = (
            self._normalize_postmortem_fields(
                record
            )
        )

        return PostmortemRecord(
            record_id=self._get_string(
                normalized,
                "record_id",
            ),

            person_id=self._get_string(
                normalized,
                "person_id",
            ),

            deceased_name=self._get_string(
                normalized,
                "deceased_name",
            ),

            first_name=self._get_string(
                normalized,
                "first_name",
            ),

            middle_name=self._get_string(
                normalized,
                "middle_name",
            ),

            last_name=self._get_string(
                normalized,
                "last_name",
            ),

            case_reference=self._get_string(
                normalized,
                "case_reference",
            ),

            fir_reference=self._get_string(
                normalized,
                "fir_reference",
            ),

            examination_timestamp=(
                self._normalize_datetime(
                    normalized.get(
                        "examination_timestamp"
                    )
                )
            ),

            facility_id=self._get_string(
                normalized,
                "facility_id",
            ),

            facility_name=self._get_string(
                normalized,
                "facility_name",
            ),

            examiner_name=self._get_string(
                normalized,
                "examiner_name",
            ),

            examiner_id=self._get_string(
                normalized,
                "examiner_id",
            ),

            cause_of_death=self._get_string(
                normalized,
                "cause_of_death",
            ),

            manner_of_death=self._get_string(
                normalized,
                "manner_of_death",
            ),

            injury_findings=self._get_string(
                normalized,
                "injury_findings",
            ),

            pathology_findings=self._get_string(
                normalized,
                "pathology_findings",
            ),

            toxicology_findings=self._get_string(
                normalized,
                "toxicology_findings",
            ),

            identification_status=(
                self._normalize_status(
                    normalized.get(
                        "identification_status"
                    )
                )
            ),

            estimated_time_of_death=(
                self._normalize_datetime(
                    normalized.get(
                        "estimated_time_of_death"
                    )
                )
            ),

            death_location=self._get_string(
                normalized,
                "death_location",
            ),

            status=self._normalize_status(
                normalized.get("status")
            ),

            source_system=self._get_string(
                normalized,
                "source_system",
            ),

            source_file=source_file,

            metadata={
                "source": "postmortem",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_postmortem_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert source-specific field names into canonical
        postmortem fields.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                POSTMORTEM_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Datetime fields
            # ------------------------------------------------

            if canonical_key in {
                "examination_timestamp",
                "estimated_time_of_death",
            }:

                normalized_value = (
                    self._normalize_datetime(
                        value
                    )
                )

            else:

                normalized_value = (
                    self.normalizer.normalize_value(
                        canonical_key,
                        value,
                    )
                )

            # ------------------------------------------------
            # Collision handling
            # ------------------------------------------------

            if canonical_key in normalized:

                existing = normalized[
                    canonical_key
                ]

                if existing in (
                    None,
                    "",
                ):

                    normalized[canonical_key] = (
                        normalized_value
                    )

                elif normalized_value in (
                    None,
                    "",
                ):

                    continue

                else:

                    normalized[
                        f"{canonical_key}_alternate"
                    ] = normalized_value

            else:

                normalized[canonical_key] = (
                    normalized_value
                )

        return normalized

    # ========================================================
    # DATETIME
    # ========================================================

    def _normalize_datetime(
        self,
        value: Any,
    ) -> str | None:
        """
        Normalize a date/time value.
        """

        if value is None:
            return None

        try:

            return self.normalizer.normalize_datetime(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return self._get_text(value)

    # ========================================================
    # STATUS
    # ========================================================

    @staticmethod
    def _normalize_status(
        value: Any,
    ) -> str | None:
        """
        Normalize descriptive status values.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value.upper()

    # ========================================================
    # STRING
    # ========================================================

    @staticmethod
    def _get_string(
        record: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Safely retrieve a string field.
        """

        return PostmortemRecordProcessor._get_text(
            record.get(key)
        )

    @staticmethod
    def _get_text(
        value: Any,
    ) -> str | None:
        """
        Convert a value into cleaned text.
        """

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    # ========================================================
    # MINIMUM FIELD CHECK
    # ========================================================

    @staticmethod
    def validate_minimum_postmortem_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify missing fields useful for postmortem record
        identification.

        Missing fields are reported rather than automatically
        rejecting the record.
        """

        missing: list[str] = []

        if not record.get("record_id"):
            missing.append("record_id")

        if not record.get("case_reference"):
            missing.append("case_reference")

        if not any(
            record.get(field_name)
            for field_name in (
                "person_id",
                "deceased_name",
            )
        ):
            missing.append(
                "person_id/deceased_name"
            )

        return missing


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_postmortem_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> PostmortemProcessingResult:
    """
    Convenience function for processing postmortem records.
    """

    processor = PostmortemRecordProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
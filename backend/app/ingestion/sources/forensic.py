"""
TRINETRA Forensic Evidence Ingestion
====================================

Forensic-evidence-specific ingestion and normalization.

Responsibilities
----------------
- Normalize evidence identifiers
- Normalize evidence types
- Preserve evidence descriptions
- Normalize collection timestamps
- Preserve collection location
- Preserve collector information
- Preserve laboratory information
- Preserve examination/test information
- Preserve forensic findings
- Preserve case/FIR references
- Prepare records for entity linking
- Prepare records for graph construction

This module does NOT:
- determine guilt
- determine whether evidence proves involvement
- automatically identify a suspect
- fabricate forensic conclusions
- modify laboratory findings
- infer conclusions from incomplete evidence

Forensic conclusions should come from authorized forensic processes,
validated laboratory results, and later analytical modules.
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

FORENSIC_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Evidence identifiers
    # --------------------------------------------------------

    "evidence_id": "evidence_id",
    "evidence_identifier": "evidence_id",
    "exhibit_id": "evidence_id",
    "exhibit_number": "evidence_id",
    "item_id": "evidence_id",

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
    # Evidence type
    # --------------------------------------------------------

    "type": "evidence_type",
    "evidence_category": "evidence_type",
    "exhibit_type": "evidence_type",
    "item_type": "evidence_type",

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    "description": "description",
    "evidence_description": "description",
    "item_description": "description",
    "exhibit_description": "description",

    # --------------------------------------------------------
    # Collection
    # --------------------------------------------------------

    "collection_date": "collection_timestamp",
    "date_collected": "collection_timestamp",
    "collected_at": "collection_timestamp",
    "collection_time": "collection_timestamp",

    "collection_location": "collection_location",
    "place_collected": "collection_location",
    "location_collected": "collection_location",

    # --------------------------------------------------------
    # Collector
    # --------------------------------------------------------

    "collector": "collector_name",
    "collected_by": "collector_name",
    "collector_name": "collector_name",
    "officer_collected": "collector_name",

    "collector_id": "collector_id",
    "officer_id": "collector_id",

    # --------------------------------------------------------
    # Laboratory
    # --------------------------------------------------------

    "lab": "laboratory_name",
    "laboratory": "laboratory_name",
    "lab_name": "laboratory_name",

    "lab_id": "laboratory_id",
    "laboratory_id": "laboratory_id",

    # --------------------------------------------------------
    # Examination
    # --------------------------------------------------------

    "examination": "examination_type",
    "examination_type": "examination_type",
    "test_type": "examination_type",
    "forensic_test": "examination_type",

    "examination_date": "examination_timestamp",
    "examined_at": "examination_timestamp",
    "test_date": "examination_timestamp",

    # --------------------------------------------------------
    # Findings
    # --------------------------------------------------------

    "finding": "findings",
    "findings": "findings",
    "forensic_finding": "findings",
    "laboratory_finding": "findings",
    "result": "findings",
    "test_result": "findings",

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    "evidence_status": "status",
    "exhibit_status": "status",
    "processing_status": "status",

    # --------------------------------------------------------
    # Chain of custody
    # --------------------------------------------------------

    "custody_status": "chain_of_custody_status",
    "chain_status": "chain_of_custody_status",
    "chain_of_custody": "chain_of_custody_status",

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    "source": "source_system",
    "data_source": "source_system",
    "source_system": "source_system",
}


# ============================================================
# FORENSIC RECORD
# ============================================================


@dataclass
class ForensicRecord:
    """
    Canonical representation of a forensic evidence record.

    This object belongs to the ingestion layer and remains
    independent from database models.
    """

    evidence_id: str | None = None

    case_reference: str | None = None

    fir_reference: str | None = None

    evidence_type: str | None = None

    description: str | None = None

    collection_timestamp: str | None = None

    collection_location: str | None = None

    collector_name: str | None = None

    collector_id: str | None = None

    laboratory_name: str | None = None

    laboratory_id: str | None = None

    examination_type: str | None = None

    examination_timestamp: str | None = None

    findings: str | None = None

    status: str | None = None

    chain_of_custody_status: str | None = None

    source_system: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # GRAPH REPRESENTATION
    # ========================================================

    @property
    def graph_entity(self) -> dict[str, Any]:
        """
        Return a graph-oriented representation.

        The graph builder decides which relationships should
        actually be created.
        """

        return {
            "entity_type": "FORENSIC_EVIDENCE",
            "evidence_id": self.evidence_id,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
            "evidence_type": self.evidence_type,
            "collection_timestamp": (
                self.collection_timestamp
            ),
            "collection_location": (
                self.collection_location
            ),
            "laboratory_name": self.laboratory_name,
            "examination_type": self.examination_type,
            "status": self.status,
        }

    # ========================================================
    # ENTITY LINKING CANDIDATE
    # ========================================================

    @property
    def entity_link_candidate(self) -> dict[str, Any]:
        """
        Return information that can be supplied to the
        entity-linking layer.

        This does not establish a relationship automatically.
        """

        return {
            "evidence_id": self.evidence_id,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
            "evidence_type": self.evidence_type,
            "collection_location": (
                self.collection_location
            ),
            "collector_id": self.collector_id,
            "laboratory_id": self.laboratory_id,
        }

    # ========================================================
    # NLP TEXT
    # ========================================================

    @property
    def nlp_text(self) -> str:
        """
        Return descriptive forensic text for the NLP layer.

        NLP can later extract entities such as:
        - people
        - locations
        - organizations
        - dates
        - case references
        - objects
        - forensic terminology
        """

        parts: list[str] = []

        if self.evidence_type:
            parts.append(
                f"Evidence Type: {self.evidence_type}"
            )

        if self.description:
            parts.append(
                f"Description: {self.description}"
            )

        if self.findings:
            parts.append(
                f"Findings: {self.findings}"
            )

        if self.collection_location:
            parts.append(
                f"Collection Location: "
                f"{self.collection_location}"
            )

        if self.examination_type:
            parts.append(
                f"Examination Type: "
                f"{self.examination_type}"
            )

        return "\n".join(parts)

    # ========================================================
    # DICTIONARY
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert record to dictionary.
        """

        return asdict(self)


# ============================================================
# PROCESSING RESULT
# ============================================================


@dataclass
class ForensicProcessingResult:
    """
    Result returned after forensic processing.
    """

    records: list[ForensicRecord]

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
        Convert result into a dictionary.
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
# FORENSIC PROCESSOR
# ============================================================


class ForensicRecordProcessor:
    """
    Processes authorized forensic evidence records into a
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
    ) -> ForensicProcessingResult:
        """
        Process multiple forensic records.
        """

        records = list(records)

        processed: list[
            ForensicRecord
        ] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_forensic_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            forensic_record = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(
                forensic_record
            )

        return ForensicProcessingResult(
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
    ) -> ForensicRecord:
        """
        Convert one generic record into a ForensicRecord.
        """

        normalized = (
            self._normalize_forensic_fields(
                record
            )
        )

        return ForensicRecord(
            evidence_id=self._get_string(
                normalized,
                "evidence_id",
            ),

            case_reference=self._get_string(
                normalized,
                "case_reference",
            ),

            fir_reference=self._get_string(
                normalized,
                "fir_reference",
            ),

            evidence_type=self._get_string(
                normalized,
                "evidence_type",
            ),

            description=self._get_string(
                normalized,
                "description",
            ),

            collection_timestamp=(
                self._normalize_datetime(
                    normalized.get(
                        "collection_timestamp"
                    )
                )
            ),

            collection_location=self._get_string(
                normalized,
                "collection_location",
            ),

            collector_name=self._get_string(
                normalized,
                "collector_name",
            ),

            collector_id=self._get_string(
                normalized,
                "collector_id",
            ),

            laboratory_name=self._get_string(
                normalized,
                "laboratory_name",
            ),

            laboratory_id=self._get_string(
                normalized,
                "laboratory_id",
            ),

            examination_type=self._get_string(
                normalized,
                "examination_type",
            ),

            examination_timestamp=(
                self._normalize_datetime(
                    normalized.get(
                        "examination_timestamp"
                    )
                )
            ),

            findings=self._get_string(
                normalized,
                "findings",
            ),

            status=self._normalize_status(
                normalized.get("status")
            ),

            chain_of_custody_status=(
                self._normalize_status(
                    normalized.get(
                        "chain_of_custody_status"
                    )
                )
            ),

            source_system=self._get_string(
                normalized,
                "source_system",
            ),

            source_file=source_file,

            metadata={
                "source": "forensic",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_forensic_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert source-specific field names into canonical
        forensic fields.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                FORENSIC_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Datetime fields
            # ------------------------------------------------

            if canonical_key in {
                "collection_timestamp",
                "examination_timestamp",
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
        Normalize a forensic date/time value.
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

        return ForensicRecordProcessor._get_text(
            record.get(key)
        )

    @staticmethod
    def _get_text(
        value: Any,
    ) -> str | None:
        """
        Convert a value to cleaned text.
        """

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    # ========================================================
    # MINIMUM FIELD CHECK
    # ========================================================

    @staticmethod
    def validate_minimum_forensic_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify missing fields useful for evidence
        identification.

        Missing fields are reported rather than automatically
        rejecting the record.
        """

        missing: list[str] = []

        if not record.get("evidence_id"):

            missing.append("evidence_id")

        if not record.get("case_reference"):

            missing.append("case_reference")

        if not record.get("evidence_type"):

            missing.append("evidence_type")

        return missing


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_forensic_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> ForensicProcessingResult:
    """
    Convenience function for processing forensic records.
    """

    processor = ForensicRecordProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
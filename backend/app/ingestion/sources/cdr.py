"""
TRINETRA CDR Ingestion
======================

CDR = Call Detail Record

This module converts generic parsed/normalized CDR data into
a canonical internal representation.

Responsibilities
----------------
- Normalize caller/callee information
- Normalize call timestamps
- Normalize call duration
- Preserve cell/location metadata when legitimately available
- Prepare communication records for entity linking
- Prepare records for graph construction

This module does NOT:
- intercept communications
- access telecom networks
- identify a person solely from a phone number
- determine guilt
- assign suspect probability
- perform risk scoring

Those operations belong to later authorized analytical stages.
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
# CDR FIELD ALIASES
# ============================================================

CDR_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Caller
    # --------------------------------------------------------

    "caller": "caller_phone",
    "caller_number": "caller_phone",
    "calling_number": "caller_phone",
    "calling_party": "caller_phone",
    "originating_number": "caller_phone",
    "source_number": "caller_phone",

    # --------------------------------------------------------
    # Callee
    # --------------------------------------------------------

    "callee": "callee_phone",
    "callee_number": "callee_phone",
    "called_number": "callee_phone",
    "receiving_number": "callee_phone",
    "called_party": "callee_phone",
    "destination_number": "callee_phone",

    # --------------------------------------------------------
    # Date / time
    # --------------------------------------------------------

    "call_date": "timestamp",
    "call_datetime": "timestamp",
    "call_time": "timestamp",
    "event_time": "timestamp",
    "event_datetime": "timestamp",
    "date_time": "timestamp",

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    "call_duration": "duration",
    "duration_seconds": "duration",
    "duration_sec": "duration",
    "call_length": "duration",

    # --------------------------------------------------------
    # Call type
    # --------------------------------------------------------

    "call_category": "call_type",
    "communication_type": "call_type",
    "type": "call_type",

    # --------------------------------------------------------
    # Cell tower
    # --------------------------------------------------------

    "cell_id": "cell_id",
    "cell_tower": "cell_id",
    "tower_id": "cell_id",
    "site_id": "cell_id",

    # --------------------------------------------------------
    # Cell location
    # --------------------------------------------------------

    "cell_location": "location",
    "tower_location": "location",

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    "lat": "latitude",
    "lng": "longitude",
    "lon": "longitude",

    # --------------------------------------------------------
    # SIM / subscriber
    # --------------------------------------------------------

    "sim_number": "sim_id",
    "sim_id": "sim_id",
    "subscriber_id": "subscriber_id",
    "imsi": "imsi",

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    "device_id": "imei",
    "device_imei": "imei",

    # --------------------------------------------------------
    # Record identifier
    # --------------------------------------------------------

    "cdr_id": "record_id",
    "record_identifier": "record_id",
    "record_no": "record_id",
}


# ============================================================
# CDR RECORD
# ============================================================


@dataclass
class CDRRecord:
    """
    Canonical internal representation of one CDR record.

    The object remains separate from the database model so
    ingestion can evolve independently from persistence.
    """

    record_id: str | None = None

    caller_phone: str | None = None

    callee_phone: str | None = None

    timestamp: str | None = None

    duration: float | None = None

    call_type: str | None = None

    cell_id: str | None = None

    location: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    sim_id: str | None = None

    subscriber_id: str | None = None

    imsi: str | None = None

    imei: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # GRAPH RELATIONSHIP DESCRIPTION
    # ========================================================

    @property
    def graph_relationship(self) -> dict[str, Any]:
        """
        Return a graph-oriented representation.

        This is descriptive data for the later graph builder;
        it does not itself create a Neo4j relationship.
        """

        return {
            "relationship": "COMMUNICATED_WITH",
            "source_phone": self.caller_phone,
            "target_phone": self.callee_phone,
            "timestamp": self.timestamp,
            "duration": self.duration,
            "call_type": self.call_type,
            "cell_id": self.cell_id,
        }

    # ========================================================
    # DICTIONARY
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the CDR record to a dictionary.
        """

        return asdict(self)


# ============================================================
# CDR PROCESSING RESULT
# ============================================================


@dataclass
class CDRProcessingResult:
    """
    Result returned by the CDR processor.
    """

    records: list[CDRRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of processed CDR records.
        """

        return len(self.records)

    @property
    def has_validation_errors(self) -> bool:
        """
        Return True when at least one error-level issue exists.
        """

        return any(
            issue.severity == "error"
            for issue in self.validation_issues
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the complete result to a dictionary.
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
# CDR PROCESSOR
# ============================================================


class CDRProcessor:
    """
    Processes normalized CDR records.

    Example:

        processor = CDRProcessor()

        result = processor.process_records(
            records,
            source_file="cdr_001.csv",
        )
    """

    def __init__(self) -> None:

        self.normalizer = DataNormalizer()

        self.validator = RecordValidator()

    # ========================================================
    # PROCESS MULTIPLE RECORDS
    # ========================================================

    def process_records(
        self,
        records: Iterable[dict[str, Any]],
        source_file: str | None = None,
    ) -> CDRProcessingResult:
        """
        Process multiple CDR records.
        """

        records = list(records)

        processed: list[CDRRecord] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = self._normalize_cdr_fields(
                record
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            cdr = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(cdr)

        return CDRProcessingResult(
            records=processed,
            validation_issues=validation_issues,
            source_file=source_file,
        )

    # ========================================================
    # PROCESS SINGLE RECORD
    # ========================================================

    def process_record(
        self,
        record: dict[str, Any],
        source_file: str | None = None,
    ) -> CDRRecord:
        """
        Convert one generic record into a CDRRecord.
        """

        normalized = self._normalize_cdr_fields(
            record
        )

        return CDRRecord(
            record_id=self._get_string(
                normalized,
                "record_id",
            ),

            caller_phone=self._get_string(
                normalized,
                "caller_phone",
            ),

            callee_phone=self._get_string(
                normalized,
                "callee_phone",
            ),

            timestamp=self._get_string(
                normalized,
                "timestamp",
            ),

            duration=self._normalize_duration(
                normalized.get("duration")
            ),

            call_type=self._get_string(
                normalized,
                "call_type",
            ),

            cell_id=self._get_string(
                normalized,
                "cell_id",
            ),

            location=self._get_string(
                normalized,
                "location",
            ),

            latitude=self._normalize_coordinate(
                normalized.get("latitude")
            ),

            longitude=self._normalize_coordinate(
                normalized.get("longitude")
            ),

            sim_id=self._get_string(
                normalized,
                "sim_id",
            ),

            subscriber_id=self._get_string(
                normalized,
                "subscriber_id",
            ),

            imsi=self._get_string(
                normalized,
                "imsi",
            ),

            imei=self._get_string(
                normalized,
                "imei",
            ),

            source_file=source_file,

            metadata={
                "source": "cdr",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_cdr_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert source-specific CDR field names into canonical
        names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = CDR_FIELD_ALIASES.get(
                generic_key,
                generic_key,
            )

            normalized_value = (
                self.normalizer.normalize_value(
                    canonical_key,
                    value,
                )
            )

            # ------------------------------------------------
            # Preserve collisions
            # ------------------------------------------------

            if canonical_key in normalized:

                existing = normalized[
                    canonical_key
                ]

                if existing in (None, ""):

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
    # DURATION
    # ========================================================

    @staticmethod
    def _normalize_duration(
        value: Any,
    ) -> float | None:
        """
        Convert duration into seconds.

        Supported examples:

            120
            "120"
            "120 seconds"
            "00:02:00"
        """

        if value is None:
            return None

        if isinstance(value, (int, float)):

            return float(value)

        value = str(value).strip()

        if not value:
            return None

        # ----------------------------------------------------
        # HH:MM:SS
        # ----------------------------------------------------

        if ":" in value:

            parts = value.split(":")

            if len(parts) == 3:

                try:

                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])

                    return (
                        hours * 3600
                        + minutes * 60
                        + seconds
                    )

                except ValueError:
                    pass

            elif len(parts) == 2:

                try:

                    minutes = float(parts[0])
                    seconds = float(parts[1])

                    return (
                        minutes * 60
                        + seconds
                    )

                except ValueError:
                    pass

        # ----------------------------------------------------
        # Numeric text
        # ----------------------------------------------------

        cleaned = ""

        for character in value:

            if character.isdigit() or character == ".":

                cleaned += character

        if not cleaned:
            return None

        try:

            return float(cleaned)

        except ValueError:

            return None

    # ========================================================
    # COORDINATE
    # ========================================================

    @staticmethod
    def _normalize_coordinate(
        value: Any,
    ) -> float | None:
        """
        Convert coordinate to float.
        """

        if value is None:
            return None

        try:

            return float(value)

        except (TypeError, ValueError):

            return None

    # ========================================================
    # STRING HELPER
    # ========================================================

    @staticmethod
    def _get_string(
        record: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Safely retrieve a value as a string.
        """

        value = record.get(key)

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    # ========================================================
    # MINIMUM FIELD CHECK
    # ========================================================

    @staticmethod
    def validate_minimum_cdr_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Return important CDR fields that are missing.

        Missing values are reported rather than automatically
        rejecting the record.
        """

        recommended_fields = (
            "caller_phone",
            "callee_phone",
            "timestamp",
        )

        missing: list[str] = []

        for field_name in recommended_fields:

            value = record.get(field_name)

            if value is None:

                missing.append(field_name)

            elif (
                isinstance(value, str)
                and not value.strip()
            ):

                missing.append(field_name)

        return missing


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_cdr_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> CDRProcessingResult:
    """
    Convenience function for processing CDR records.
    """

    processor = CDRProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
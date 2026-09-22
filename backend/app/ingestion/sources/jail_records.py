"""
TRINETRA Jail Records Ingestion
===============================

Jail/custody-record ingestion and normalization.

Responsibilities
----------------
- Normalize custody-record identifiers
- Normalize person identifiers
- Normalize names
- Normalize dates
- Preserve custody/facility information
- Preserve case/reference information
- Preserve release/status information
- Prepare records for entity linking
- Prepare records for graph construction

This module does NOT:
- determine whether a person is currently dangerous
- determine guilt
- assign a criminal-risk score
- infer criminal behavior from custody history
- access restricted correctional systems

Only authorized records should be supplied to this pipeline.
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

JAIL_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Record identifiers
    # --------------------------------------------------------

    "record_id": "record_id",
    "custody_record_id": "record_id",
    "jail_record_id": "record_id",
    "inmate_record_id": "record_id",

    # --------------------------------------------------------
    # Person identifiers
    # --------------------------------------------------------

    "person_id": "person_id",
    "person_identifier": "person_id",
    "individual_id": "person_id",
    "individual_identifier": "person_id",

    "inmate_id": "inmate_id",
    "inmate_number": "inmate_id",
    "prisoner_id": "inmate_id",
    "prisoner_number": "inmate_id",

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    "name": "person_name",
    "full_name": "person_name",
    "inmate_name": "person_name",
    "prisoner_name": "person_name",
    "individual_name": "person_name",

    "first_name": "first_name",
    "middle_name": "middle_name",
    "last_name": "last_name",
    "surname": "last_name",

    # --------------------------------------------------------
    # Date of birth
    # --------------------------------------------------------

    "dob": "date_of_birth",
    "birth_date": "date_of_birth",
    "date_birth": "date_of_birth",

    # --------------------------------------------------------
    # Custody dates
    # --------------------------------------------------------

    "admission_date": "admission_date",
    "entry_date": "admission_date",
    "date_of_admission": "admission_date",
    "incarceration_date": "admission_date",

    "release_date": "release_date",
    "date_of_release": "release_date",
    "discharge_date": "release_date",

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    "jail": "facility_name",
    "jail_name": "facility_name",
    "prison": "facility_name",
    "prison_name": "facility_name",
    "correctional_facility": "facility_name",
    "facility": "facility_name",

    "facility_id": "facility_id",
    "jail_id": "facility_id",
    "prison_id": "facility_id",

    # --------------------------------------------------------
    # Custody status
    # --------------------------------------------------------

    "custody_status": "status",
    "inmate_status": "status",
    "prisoner_status": "status",
    "current_status": "status",

    # --------------------------------------------------------
    # Case/reference
    # --------------------------------------------------------

    "case_number": "case_reference",
    "case_no": "case_reference",
    "case_id": "case_reference",
    "case_reference_number": "case_reference",

    "fir_number": "fir_reference",
    "fir_no": "fir_reference",

    "court_case": "court_reference",
    "court_case_number": "court_reference",

    # --------------------------------------------------------
    # Offence/charge
    # --------------------------------------------------------

    "charge": "charges",
    "charges": "charges",
    "offence": "charges",
    "offense": "charges",
    "offence_description": "charges",
    "offense_description": "charges",

    # --------------------------------------------------------
    # Court information
    # --------------------------------------------------------

    "court": "court_name",
    "court_name": "court_name",

    "court_status": "court_status",
    "legal_status": "court_status",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "location": "location",
    "facility_location": "location",
    "jail_location": "location",

    # --------------------------------------------------------
    # Source metadata
    # --------------------------------------------------------

    "source": "source_system",
    "database_source": "source_system",
    "record_source": "source_system",
}


# ============================================================
# JAIL RECORD
# ============================================================


@dataclass
class JailRecord:
    """
    Canonical representation of a custody/jail record.

    This object belongs to the ingestion layer and is independent
    of the database models.
    """

    record_id: str | None = None

    person_id: str | None = None

    inmate_id: str | None = None

    person_name: str | None = None

    first_name: str | None = None

    middle_name: str | None = None

    last_name: str | None = None

    date_of_birth: str | None = None

    admission_date: str | None = None

    release_date: str | None = None

    facility_id: str | None = None

    facility_name: str | None = None

    status: str | None = None

    case_reference: str | None = None

    fir_reference: str | None = None

    court_reference: str | None = None

    charges: list[str] = field(
        default_factory=list
    )

    court_name: str | None = None

    court_status: str | None = None

    location: str | None = None

    source_system: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # DISPLAY NAME
    # ========================================================

    @property
    def resolved_name(self) -> str | None:
        """
        Return the best available representation of the person's
        name.

        The value is only a source-data representation and does
        not establish identity with another person record.
        """

        if self.person_name:
            return self.person_name

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

        The graph builder later decides which nodes and
        relationships should be created.
        """

        return {
            "entity_type": "CUSTODY_RECORD",
            "record_id": self.record_id,
            "person_id": self.person_id,
            "inmate_id": self.inmate_id,
            "person_name": self.resolved_name,
            "facility_id": self.facility_id,
            "facility_name": self.facility_name,
            "status": self.status,
            "admission_date": self.admission_date,
            "release_date": self.release_date,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
        }

    # ========================================================
    # ENTITY LINK
    # ========================================================

    @property
    def entity_link_candidate(self) -> dict[str, Any]:
        """
        Return source attributes that can be supplied to the
        entity-linking layer.

        These attributes are candidate evidence only.

        The entity linker must determine whether this record
        actually corresponds to an existing Person entity.
        """

        return {
            "person_id": self.person_id,
            "inmate_id": self.inmate_id,
            "name": self.resolved_name,
            "date_of_birth": self.date_of_birth,
            "case_reference": self.case_reference,
            "fir_reference": self.fir_reference,
        }

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
class JailProcessingResult:
    """
    Result returned after processing jail records.
    """

    records: list[JailRecord]

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
        Check whether any error-level validation issue exists.
        """

        return any(
            issue.severity == "error"
            for issue in self.validation_issues
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the processing result to a dictionary.
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
# JAIL PROCESSOR
# ============================================================


class JailRecordProcessor:
    """
    Processes authorized custody/jail records into a canonical
    structure.
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
    ) -> JailProcessingResult:
        """
        Process multiple jail/custody records.
        """

        records = list(records)

        processed: list[JailRecord] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_jail_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            jail_record = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(jail_record)

        return JailProcessingResult(
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
    ) -> JailRecord:
        """
        Convert one generic record into a JailRecord.
        """

        normalized = (
            self._normalize_jail_fields(
                record
            )
        )

        return JailRecord(
            record_id=self._get_string(
                normalized,
                "record_id",
            ),

            person_id=self._get_string(
                normalized,
                "person_id",
            ),

            inmate_id=self._get_string(
                normalized,
                "inmate_id",
            ),

            person_name=self._get_string(
                normalized,
                "person_name",
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

            date_of_birth=self._normalize_date(
                normalized.get(
                    "date_of_birth"
                )
            ),

            admission_date=self._normalize_date(
                normalized.get(
                    "admission_date"
                )
            ),

            release_date=self._normalize_date(
                normalized.get(
                    "release_date"
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

            status=self._normalize_status(
                normalized.get("status")
            ),

            case_reference=self._get_string(
                normalized,
                "case_reference",
            ),

            fir_reference=self._get_string(
                normalized,
                "fir_reference",
            ),

            court_reference=self._get_string(
                normalized,
                "court_reference",
            ),

            charges=self._normalize_list(
                normalized.get("charges")
            ),

            court_name=self._get_string(
                normalized,
                "court_name",
            ),

            court_status=self._normalize_status(
                normalized.get("court_status")
            ),

            location=self._get_string(
                normalized,
                "location",
            ),

            source_system=self._get_string(
                normalized,
                "source_system",
            ),

            source_file=source_file,

            metadata={
                "source": "jail_records",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_jail_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert source-specific field names into canonical names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                JAIL_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Date fields
            # ------------------------------------------------

            if canonical_key in {
                "date_of_birth",
                "admission_date",
                "release_date",
            }:

                normalized_value = (
                    self._normalize_date(value)
                )

            # ------------------------------------------------
            # Charges
            # ------------------------------------------------

            elif canonical_key == "charges":

                normalized_value = (
                    self._normalize_list(value)
                )

            else:

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

                if existing in (
                    None,
                    "",
                    [],
                ):

                    normalized[canonical_key] = (
                        normalized_value
                    )

                elif normalized_value in (
                    None,
                    "",
                    [],
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
    # DATE
    # ========================================================

    def _normalize_date(
        self,
        value: Any,
    ) -> str | None:
        """
        Normalize a date/datetime using the shared normalizer.
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
        Normalize descriptive custody/legal status.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value.upper()

    # ========================================================
    # LIST
    # ========================================================

    @staticmethod
    def _normalize_list(
        value: Any,
    ) -> list[str]:
        """
        Normalize list-like fields such as charges.

        Supports:

            ["Charge A", "Charge B"]

        and:

            "Charge A, Charge B"
        """

        if value is None:
            return []

        if isinstance(
            value,
            (list, tuple, set),
        ):

            values = list(value)

        else:

            text = str(value).strip()

            if not text:
                return []

            values = text.split(",")

        result: list[str] = []

        for item in values:

            item = str(item).strip()

            if not item:
                continue

            if item not in result:

                result.append(item)

        return result

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

        value = record.get(key)

        return JailRecordProcessor._get_text(
            value
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
    def validate_minimum_jail_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify useful identifying fields that are missing.

        Missing fields are reported rather than automatically
        rejecting a record.
        """

        identity_fields = (
            "person_id",
            "inmate_id",
            "person_name",
        )

        if any(
            record.get(field_name)
            for field_name in identity_fields
        ):
            return []

        return [
            "person_id/inmate_id/person_name"
        ]


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_jail_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> JailProcessingResult:
    """
    Convenience function for processing jail records.
    """

    processor = JailRecordProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
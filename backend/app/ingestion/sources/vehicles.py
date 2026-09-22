"""
TRINETRA Vehicle Records Ingestion
===================================

Vehicle-specific ingestion and normalization.

Responsibilities
----------------
- Normalize vehicle registration numbers
- Normalize vehicle make/model information
- Normalize owner references
- Normalize registration dates
- Preserve vehicle status and classification
- Preserve location information
- Prepare vehicle records for entity linking
- Prepare records for graph construction

This module does NOT:
- determine whether a vehicle is involved in a crime
- determine whether an owner is a suspect
- assign risk scores
- access restricted vehicle databases
- perform real-time vehicle tracking

Those decisions belong to later authorized analytical stages.
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
# VEHICLE FIELD ALIASES
# ============================================================

VEHICLE_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Vehicle identification
    # --------------------------------------------------------

    "vehicle_id": "vehicle_id",
    "vehicle_identifier": "vehicle_id",
    "vehicle_record_id": "vehicle_id",

    # --------------------------------------------------------
    # Registration number
    # --------------------------------------------------------

    "vehicle_number": "registration_number",
    "vehicle_registration": "registration_number",
    "registration_no": "registration_number",
    "registration_number": "registration_number",
    "reg_number": "registration_number",
    "plate_number": "registration_number",
    "number_plate": "registration_number",
    "license_plate": "registration_number",

    # --------------------------------------------------------
    # Owner
    # --------------------------------------------------------

    "owner": "owner_name",
    "owner_name": "owner_name",
    "registered_owner": "owner_name",
    "vehicle_owner": "owner_name",

    "owner_id": "owner_id",
    "owner_identifier": "owner_id",

    # --------------------------------------------------------
    # Vehicle make/model
    # --------------------------------------------------------

    "manufacturer": "make",
    "vehicle_make": "make",
    "brand": "make",

    "vehicle_model": "model",
    "model_name": "model",

    # --------------------------------------------------------
    # Vehicle type
    # --------------------------------------------------------

    "vehicle_category": "vehicle_type",
    "category": "vehicle_type",
    "vehicle_class": "vehicle_type",

    # --------------------------------------------------------
    # Color
    # --------------------------------------------------------

    "vehicle_colour": "color",
    "vehicle_color": "color",

    # --------------------------------------------------------
    # Registration
    # --------------------------------------------------------

    "registration_date": "registration_date",
    "date_of_registration": "registration_date",

    "registration_authority": "registration_authority",
    "rto": "registration_authority",
    "rto_name": "registration_authority",

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    "vehicle_status": "status",
    "registration_status": "status",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "registered_location": "location",
    "vehicle_location": "location",
    "location_name": "location",

    # --------------------------------------------------------
    # Chassis / engine
    # --------------------------------------------------------

    "chassis_no": "chassis_number",
    "chassis_id": "chassis_number",

    "engine_no": "engine_number",
    "engine_id": "engine_number",

    # --------------------------------------------------------
    # Insurance
    # --------------------------------------------------------

    "insurance_company": "insurance_provider",
    "insurer": "insurance_provider",

    "insurance_number": "insurance_policy_number",
    "policy_number": "insurance_policy_number",

    # --------------------------------------------------------
    # Fitness / validity
    # --------------------------------------------------------

    "fitness_expiry": "fitness_expiry_date",
    "fitness_valid_until": "fitness_expiry_date",

    "registration_expiry": "registration_expiry_date",
    "registration_valid_until": "registration_expiry_date",

    # --------------------------------------------------------
    # Source metadata
    # --------------------------------------------------------

    "source": "source_system",
    "database_source": "source_system",
}


# ============================================================
# VEHICLE RECORD
# ============================================================


@dataclass
class VehicleRecord:
    """
    Canonical internal representation of a vehicle record.

    This object belongs to the ingestion layer and is kept
    independent from the database model.
    """

    vehicle_id: str | None = None

    registration_number: str | None = None

    owner_name: str | None = None

    owner_id: str | None = None

    make: str | None = None

    model: str | None = None

    vehicle_type: str | None = None

    color: str | None = None

    registration_date: str | None = None

    registration_authority: str | None = None

    status: str | None = None

    location: str | None = None

    chassis_number: str | None = None

    engine_number: str | None = None

    insurance_provider: str | None = None

    insurance_policy_number: str | None = None

    fitness_expiry_date: str | None = None

    registration_expiry_date: str | None = None

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

        The graph builder will later determine which nodes and
        relationships should actually be created.
        """

        return {
            "entity_type": "VEHICLE",
            "vehicle_id": self.vehicle_id,
            "registration_number": (
                self.registration_number
            ),
            "make": self.make,
            "model": self.model,
            "vehicle_type": self.vehicle_type,
            "color": self.color,
            "status": self.status,
        }

    # ========================================================
    # OWNER LINK
    # ========================================================

    @property
    def owner_link(self) -> dict[str, Any]:
        """
        Return information that can be supplied to the entity
        linking layer.

        This does NOT assert that an owner is connected to a
        person entity. Entity linking must establish that later.
        """

        return {
            "vehicle": self.registration_number,
            "owner_name": self.owner_name,
            "owner_id": self.owner_id,
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
class VehicleProcessingResult:
    """
    Result returned after vehicle processing.
    """

    records: list[VehicleRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of vehicle records processed.
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
# VEHICLE PROCESSOR
# ============================================================


class VehicleProcessor:
    """
    Processes vehicle records into a canonical structure.

    Example
    -------

        processor = VehicleProcessor()

        result = processor.process_records(
            records,
            source_file="vehicles.csv",
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
    ) -> VehicleProcessingResult:
        """
        Process multiple vehicle records.
        """

        records = list(records)

        processed: list[VehicleRecord] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_vehicle_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            vehicle = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(vehicle)

        return VehicleProcessingResult(
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
    ) -> VehicleRecord:
        """
        Convert one generic record into a VehicleRecord.
        """

        normalized = (
            self._normalize_vehicle_fields(
                record
            )
        )

        return VehicleRecord(
            vehicle_id=self._get_string(
                normalized,
                "vehicle_id",
            ),

            registration_number=(
                self._normalize_registration_number(
                    normalized.get(
                        "registration_number"
                    )
                )
            ),

            owner_name=self._get_string(
                normalized,
                "owner_name",
            ),

            owner_id=self._get_string(
                normalized,
                "owner_id",
            ),

            make=self._get_string(
                normalized,
                "make",
            ),

            model=self._get_string(
                normalized,
                "model",
            ),

            vehicle_type=self._get_string(
                normalized,
                "vehicle_type",
            ),

            color=self._get_string(
                normalized,
                "color",
            ),

            registration_date=self._get_string(
                normalized,
                "registration_date",
            ),

            registration_authority=(
                self._get_string(
                    normalized,
                    "registration_authority",
                )
            ),

            status=self._normalize_status(
                normalized.get("status")
            ),

            location=self._get_string(
                normalized,
                "location",
            ),

            chassis_number=self._get_string(
                normalized,
                "chassis_number",
            ),

            engine_number=self._get_string(
                normalized,
                "engine_number",
            ),

            insurance_provider=(
                self._get_string(
                    normalized,
                    "insurance_provider",
                )
            ),

            insurance_policy_number=(
                self._get_string(
                    normalized,
                    "insurance_policy_number",
                )
            ),

            fitness_expiry_date=(
                self._get_string(
                    normalized,
                    "fitness_expiry_date",
                )
            ),

            registration_expiry_date=(
                self._get_string(
                    normalized,
                    "registration_expiry_date",
                )
            ),

            source_system=self._get_string(
                normalized,
                "source_system",
            ),

            source_file=source_file,

            metadata={
                "source": "vehicles",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_vehicle_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize generic and vehicle-specific field names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                VEHICLE_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Vehicle registration numbers need special
            # normalization.
            # ------------------------------------------------

            if canonical_key == "registration_number":

                normalized_value = (
                    self._normalize_registration_number(
                        value
                    )
                )

            elif canonical_key in {
                "registration_date",
                "fitness_expiry_date",
                "registration_expiry_date",
            }:

                normalized_value = (
                    self.normalizer.normalize_datetime(
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
    # REGISTRATION NUMBER
    # ========================================================

    @staticmethod
    def _normalize_registration_number(
        value: Any,
    ) -> str | None:
        """
        Normalize a vehicle registration number.

        Example:

            "DL 01 AB 1234"
                ↓
            "DL01AB1234"
        """

        if value is None:
            return None

        value = str(value).strip().upper()

        if not value:
            return None

        return "".join(
            character
            for character in value
            if character.isalnum()
        )

    # ========================================================
    # STATUS
    # ========================================================

    @staticmethod
    def _normalize_status(
        value: Any,
    ) -> str | None:
        """
        Normalize vehicle status.

        The values are kept descriptive. The ingestion layer
        does not infer criminal or suspicious status.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value.upper()

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
    def validate_minimum_vehicle_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify important vehicle fields that are missing.

        Missing fields are reported instead of automatically
        rejecting the record.
        """

        recommended_fields = (
            "registration_number",
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


def process_vehicle_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> VehicleProcessingResult:
    """
    Convenience function for processing vehicle records.
    """

    processor = VehicleProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
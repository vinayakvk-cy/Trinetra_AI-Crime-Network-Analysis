"""
TRINETRA GPS / LOCATION INGESTION
=================================

GPS/location-specific ingestion and normalization.

Responsibilities
----------------
- Normalize GPS/device identifiers
- Normalize timestamps
- Normalize latitude and longitude
- Normalize location names
- Preserve source information
- Preserve optional movement metadata
- Prepare location records for entity linking
- Prepare records for graph construction

This module does NOT:
- track people in real time
- determine whether movement is suspicious
- determine guilt or involvement
- assign risk scores
- infer criminal activity from location alone

Only authorized and lawfully obtained location data should enter
this pipeline.
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

GPS_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Record identification
    # --------------------------------------------------------

    "record_id": "record_id",
    "location_id": "record_id",
    "gps_record_id": "record_id",
    "event_id": "record_id",

    # --------------------------------------------------------
    # Device identification
    # --------------------------------------------------------

    "device_id": "device_id",
    "device_identifier": "device_id",
    "gps_device_id": "device_id",

    "phone_id": "device_id",
    "mobile_device_id": "device_id",

    # --------------------------------------------------------
    # Person identification
    # --------------------------------------------------------

    "person_id": "person_id",
    "person_identifier": "person_id",
    "individual_id": "person_id",

    # --------------------------------------------------------
    # SIM / phone reference
    # --------------------------------------------------------

    "phone_number": "phone_number",
    "mobile_number": "phone_number",
    "msisdn": "phone_number",

    "sim_id": "sim_id",
    "sim_identifier": "sim_id",
    "iccid": "sim_id",

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    "lat": "latitude",
    "latitude": "latitude",
    "gps_latitude": "latitude",

    "lng": "longitude",
    "lon": "longitude",
    "longitude": "longitude",
    "gps_longitude": "longitude",

    # --------------------------------------------------------
    # Accuracy
    # --------------------------------------------------------

    "accuracy": "accuracy_meters",
    "gps_accuracy": "accuracy_meters",
    "accuracy_m": "accuracy_meters",
    "accuracy_meters": "accuracy_meters",

    # --------------------------------------------------------
    # Altitude
    # --------------------------------------------------------

    "alt": "altitude_meters",
    "altitude": "altitude_meters",
    "altitude_m": "altitude_meters",
    "altitude_meters": "altitude_meters",

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    "speed": "speed",
    "speed_kmh": "speed_kmh",
    "speed_km_h": "speed_kmh",
    "velocity": "speed_kmh",

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    "bearing": "bearing",
    "heading": "bearing",
    "direction": "bearing",

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    "timestamp": "timestamp",
    "datetime": "timestamp",
    "date_time": "timestamp",
    "recorded_at": "timestamp",
    "location_time": "timestamp",
    "gps_time": "timestamp",

    # --------------------------------------------------------
    # Location description
    # --------------------------------------------------------

    "location": "location_name",
    "location_name": "location_name",
    "place": "location_name",
    "place_name": "location_name",
    "address": "location_name",

    # --------------------------------------------------------
    # Administrative location
    # --------------------------------------------------------

    "city": "city",
    "district": "district",
    "state": "state",
    "country": "country",

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    "source": "source_system",
    "data_source": "source_system",
    "source_system": "source_system",
}


# ============================================================
# GPS RECORD
# ============================================================


@dataclass
class GPSRecord:
    """
    Canonical representation of a GPS/location event.

    This object is part of the ingestion layer and is intentionally
    independent from database models.
    """

    record_id: str | None = None

    device_id: str | None = None

    person_id: str | None = None

    phone_number: str | None = None

    sim_id: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    accuracy_meters: float | None = None

    altitude_meters: float | None = None

    speed_kmh: float | None = None

    bearing: float | None = None

    timestamp: str | None = None

    location_name: str | None = None

    city: str | None = None

    district: str | None = None

    state: str | None = None

    country: str | None = None

    source_system: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # COORDINATE VALIDITY
    # ========================================================

    @property
    def has_coordinates(self) -> bool:
        """
        Return True when both latitude and longitude are present.
        """

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    # ========================================================
    # GRAPH REPRESENTATION
    # ========================================================

    @property
    def graph_entity(self) -> dict[str, Any]:
        """
        Return a graph-oriented representation.

        The graph builder determines the final nodes and
        relationships.
        """

        return {
            "entity_type": "LOCATION_EVENT",
            "record_id": self.record_id,
            "device_id": self.device_id,
            "person_id": self.person_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "location_name": self.location_name,
            "city": self.city,
            "district": self.district,
            "state": self.state,
            "country": self.country,
        }

    # ========================================================
    # ENTITY LINKING CANDIDATE
    # ========================================================

    @property
    def entity_link_candidate(self) -> dict[str, Any]:
        """
        Return attributes that can be supplied to the entity
        linking layer.

        These are candidate links, not confirmed identities.
        """

        return {
            "device_id": self.device_id,
            "person_id": self.person_id,
            "phone_number": self.phone_number,
            "sim_id": self.sim_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "location_name": self.location_name,
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
class GPSProcessingResult:
    """
    Result returned after processing GPS records.
    """

    records: list[GPSRecord]

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
    def valid_coordinate_count(self) -> int:
        """
        Number of records containing valid coordinate ranges.
        """

        return sum(
            1
            for record in self.records
            if GPSRecordProcessor.coordinates_are_valid(
                record.latitude,
                record.longitude,
            )
        )

    @property
    def has_validation_errors(self) -> bool:
        """
        Check whether an error-level validation issue exists.
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
            "valid_coordinate_count": (
                self.valid_coordinate_count
            ),
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
# GPS PROCESSOR
# ============================================================


class GPSRecordProcessor:
    """
    Processes authorized GPS/location records.
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
    ) -> GPSProcessingResult:
        """
        Process multiple GPS records.
        """

        records = list(records)

        processed: list[GPSRecord] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_gps_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            gps_record = self.process_record(
                normalized,
                source_file=source_file,
            )

            # ------------------------------------------------
            # Coordinate validation
            # ------------------------------------------------

            if not self.coordinates_are_valid(
                gps_record.latitude,
                gps_record.longitude,
            ):

                # Do not create a fabricated coordinate.
                # The record remains available for other fields.
                validation_issues.append(
                    ValidationIssue(
                        record_index=index,
                        field="latitude/longitude",
                        message=(
                            "Latitude/longitude are missing "
                            "or outside valid geographic ranges."
                        ),
                        severity="warning",
                    )
                )

            processed.append(gps_record)

        return GPSProcessingResult(
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
    ) -> GPSRecord:
        """
        Convert one generic record into a GPSRecord.
        """

        normalized = (
            self._normalize_gps_fields(
                record
            )
        )

        return GPSRecord(
            record_id=self._get_string(
                normalized,
                "record_id",
            ),

            device_id=self._get_string(
                normalized,
                "device_id",
            ),

            person_id=self._get_string(
                normalized,
                "person_id",
            ),

            phone_number=(
                self._normalize_phone_reference(
                    normalized.get(
                        "phone_number"
                    )
                )
            ),

            sim_id=self._get_string(
                normalized,
                "sim_id",
            ),

            latitude=self._normalize_coordinate(
                normalized.get("latitude")
            ),

            longitude=self._normalize_coordinate(
                normalized.get("longitude")
            ),

            accuracy_meters=self._normalize_number(
                normalized.get(
                    "accuracy_meters"
                )
            ),

            altitude_meters=self._normalize_number(
                normalized.get(
                    "altitude_meters"
                )
            ),

            speed_kmh=self._normalize_number(
                normalized.get("speed_kmh")
            ),

            bearing=self._normalize_bearing(
                normalized.get("bearing")
            ),

            timestamp=self._get_string(
                normalized,
                "timestamp",
            ),

            location_name=self._get_string(
                normalized,
                "location_name",
            ),

            city=self._get_string(
                normalized,
                "city",
            ),

            district=self._get_string(
                normalized,
                "district",
            ),

            state=self._get_string(
                normalized,
                "state",
            ),

            country=self._get_string(
                normalized,
                "country",
            ),

            source_system=self._get_string(
                normalized,
                "source_system",
            ),

            source_file=source_file,

            metadata={
                "source": "gps",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_gps_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize GPS field names and values.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                GPS_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Timestamp
            # ------------------------------------------------

            if canonical_key == "timestamp":

                normalized_value = (
                    self.normalizer.normalize_datetime(
                        value
                    )
                )

            # ------------------------------------------------
            # Coordinates and numeric fields
            # ------------------------------------------------

            elif canonical_key in {
                "latitude",
                "longitude",
                "accuracy_meters",
                "altitude_meters",
                "speed_kmh",
                "bearing",
            }:

                normalized_value = (
                    self._normalize_number(
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
    # COORDINATE VALIDATION
    # ========================================================

    @staticmethod
    def coordinates_are_valid(
        latitude: float | None,
        longitude: float | None,
    ) -> bool:
        """
        Validate geographic coordinate ranges.

        Latitude:
            -90 to +90

        Longitude:
            -180 to +180
        """

        if latitude is None:
            return False

        if longitude is None:
            return False

        return (
            -90.0 <= latitude <= 90.0
            and
            -180.0 <= longitude <= 180.0
        )

    # ========================================================
    # COORDINATE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_coordinate(
        value: Any,
    ) -> float | None:
        """
        Convert a coordinate into float.
        """

        if value is None:
            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ========================================================
    # NUMERIC VALUE
    # ========================================================

    @staticmethod
    def _normalize_number(
        value: Any,
    ) -> float | None:
        """
        Normalize numeric GPS metadata.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ========================================================
    # BEARING
    # ========================================================

    @staticmethod
    def _normalize_bearing(
        value: Any,
    ) -> float | None:
        """
        Normalize compass bearing.

        Valid range:
            0 <= bearing < 360
        """

        number = (
            GPSRecordProcessor._normalize_number(
                value
            )
        )

        if number is None:
            return None

        # Normalize values such as 360 or 720.
        number = number % 360.0

        return number

    # ========================================================
    # PHONE REFERENCE
    # ========================================================

    @staticmethod
    def _normalize_phone_reference(
        value: Any,
    ) -> str | None:
        """
        Preserve phone reference in a normalized textual form.

        The actual phone-number normalization strategy can be
        expanded later in a dedicated privacy/security layer.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value

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

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    # ========================================================
    # MINIMUM FIELD CHECK
    # ========================================================

    @staticmethod
    def validate_minimum_gps_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify missing fields needed to interpret a location
        event.

        A record can still be useful even when some fields are
        missing, so this function reports missing fields rather
        than automatically rejecting the record.
        """

        missing: list[str] = []

        has_device_reference = any(
            record.get(field_name)
            for field_name in (
                "device_id",
                "person_id",
                "phone_number",
                "sim_id",
            )
        )

        if not has_device_reference:

            missing.append(
                "device_id/person_id/"
                "phone_number/sim_id"
            )

        if record.get("timestamp") in (
            None,
            "",
        ):

            missing.append("timestamp")

        if record.get("latitude") in (
            None,
            "",
        ):

            missing.append("latitude")

        if record.get("longitude") in (
            None,
            "",
        ):

            missing.append("longitude")

        return missing


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def process_gps_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> GPSProcessingResult:
    """
    Convenience function for processing GPS records.
    """

    processor = GPSRecordProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
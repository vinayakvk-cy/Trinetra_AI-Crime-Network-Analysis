"""
TRINETRA Data Normalizer
========================

Converts validated records from different data sources into
a consistent internal representation.

Pipeline:

    Raw File
        ↓
    parser.py
        ↓
    validators.py
        ↓
    normalizer.py
        ↓
    Source-specific processing
        ↓
    NLP
        ↓
    Entity Linking
        ↓
    Graph

The normalizer performs data-quality transformations such as:

    - Field-name standardization
    - String cleanup
    - Phone normalization
    - Email normalization
    - Date normalization
    - GPS normalization
    - Identifier cleanup

The normalizer does NOT:

    - Determine guilt
    - Determine suspects
    - Assign criminal risk
    - Create graph relationships
    - Perform NLP inference
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable


# ============================================================
# FIELD ALIASES
# ============================================================

FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Person
    # --------------------------------------------------------

    "person_name": "name",
    "full_name": "name",
    "individual_name": "name",
    "suspect_name": "name",
    "victim_name": "name",
    "complainant_name": "name",

    # --------------------------------------------------------
    # Phone
    # --------------------------------------------------------

    "phone": "phone_number",
    "mobile": "phone_number",
    "mobile_number": "phone_number",
    "telephone": "phone_number",
    "contact_number": "phone_number",
    "caller_number": "caller_phone",
    "callee_number": "callee_phone",

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    "email_address": "email",
    "mail": "email",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "lat": "latitude",
    "lng": "longitude",
    "lon": "longitude",

    "location_name": "location",
    "place": "location",
    "place_name": "location",
    "address": "location",

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    "event_time": "timestamp",
    "event_datetime": "timestamp",
    "date_time": "timestamp",

    "call_date": "timestamp",
    "call_datetime": "timestamp",

    "transaction_date": "timestamp",
    "transaction_datetime": "timestamp",

    # --------------------------------------------------------
    # Vehicle
    # --------------------------------------------------------

    "vehicle_number": "registration_number",
    "vehicle_registration": "registration_number",
    "registration_no": "registration_number",
    "plate_number": "registration_number",
    "number_plate": "registration_number",

    # --------------------------------------------------------
    # Case
    # --------------------------------------------------------

    "fir_no": "fir_number",
    "fir_id": "fir_number",
    "case_id": "case_number",
    "case_no": "case_number",

    # --------------------------------------------------------
    # Transaction
    # --------------------------------------------------------

    "amount_paid": "amount",
    "transaction_amount": "amount",
    "value": "amount",

    # --------------------------------------------------------
    # CDR
    # --------------------------------------------------------

    "calling_number": "caller_phone",
    "receiving_number": "callee_phone",
    "called_number": "callee_phone",
    "duration_seconds": "duration",
}


# ============================================================
# NORMALIZATION RESULT
# ============================================================


class NormalizationError(Exception):
    """
    Raised when normalization cannot be completed.
    """

    pass


# ============================================================
# NORMALIZER
# ============================================================


class DataNormalizer:
    """
    Normalizes records into a common internal representation.
    """

    # ========================================================
    # PUBLIC API
    # ========================================================

    def normalize_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize one record.

        Parameters
        ----------
        record:
            Validated source record.

        Returns
        -------
        dict
            Normalized record.
        """

        if not isinstance(record, dict):
            raise NormalizationError(
                "Record must be a dictionary."
            )

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            canonical_key = self.normalize_field_name(
                key
            )

            normalized_value = self.normalize_value(
                canonical_key,
                value,
            )

            # ------------------------------------------------
            # Avoid silently overwriting values.
            # ------------------------------------------------

            if canonical_key in normalized:

                existing_value = normalized[
                    canonical_key
                ]

                if existing_value in (None, ""):

                    normalized[canonical_key] = (
                        normalized_value
                    )

                elif normalized_value in (None, ""):

                    continue

                else:
                    # Preserve both values when aliases collide.
                    normalized[
                        f"{canonical_key}_alternate"
                    ] = normalized_value

            else:

                normalized[canonical_key] = (
                    normalized_value
                )

        return normalized

    # ========================================================
    # MULTIPLE RECORDS
    # ========================================================

    def normalize_records(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Normalize multiple records.
        """

        normalized_records: list[
            dict[str, Any]
        ] = []

        for record in records:

            normalized_records.append(
                self.normalize_record(record)
            )

        return normalized_records

    # ========================================================
    # FIELD NAME
    # ========================================================

    @staticmethod
    def normalize_field_name(
        field_name: str,
    ) -> str:
        """
        Convert a source field name into a canonical name.

        Examples:

            "Mobile Number" → "mobile_number"

            "FULL NAME" → "full_name"

            "Caller Number" → "caller_number"
        """

        if not isinstance(field_name, str):

            field_name = str(field_name)

        field_name = field_name.strip().lower()

        # Replace spaces and separators.
        field_name = re.sub(
            r"[\s\-\/]+",
            "_",
            field_name,
        )

        # Remove characters that are not useful in field names.
        field_name = re.sub(
            r"[^a-zA-Z0-9_]",
            "",
            field_name,
        )

        # Collapse repeated underscores.
        field_name = re.sub(
            r"_+",
            "_",
            field_name,
        )

        field_name = field_name.strip("_")

        return FIELD_ALIASES.get(
            field_name,
            field_name,
        )

    # ========================================================
    # VALUE NORMALIZATION
    # ========================================================

    def normalize_value(
        self,
        field_name: str,
        value: Any,
    ) -> Any:
        """
        Normalize a value according to its canonical field.
        """

        if value is None:
            return None

        # ----------------------------------------------------
        # String fields
        # ----------------------------------------------------

        if isinstance(value, str):

            value = value.strip()

            if not value:
                return None

        # ----------------------------------------------------
        # Phone numbers
        # ----------------------------------------------------

        phone_fields = {
            "phone_number",
            "caller_phone",
            "callee_phone",
        }

        if field_name in phone_fields:

            return self.normalize_phone(
                value
            )

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        if field_name == "email":

            return self.normalize_email(
                value
            )

        # ----------------------------------------------------
        # Names
        # ----------------------------------------------------

        if field_name in {
            "name",
            "person_name",
            "victim",
            "complainant",
        }:

            return self.normalize_name(
                value
            )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        if field_name in {
            "location",
            "address",
            "city",
            "state",
            "district",
            "police_station",
        }:

            return self.normalize_text(
                value
            )

        # ----------------------------------------------------
        # Vehicle registration
        # ----------------------------------------------------

        if field_name == "registration_number":

            return self.normalize_registration_number(
                value
            )

        # ----------------------------------------------------
        # Date/time
        # ----------------------------------------------------

        if field_name in {
            "timestamp",
            "incident_date",
            "fir_date",
            "created_at",
            "updated_at",
        }:

            return self.normalize_datetime(
                value
            )

        # ----------------------------------------------------
        # GPS
        # ----------------------------------------------------

        if field_name in {
            "latitude",
            "longitude",
        }:

            return self.normalize_coordinate(
                value
            )

        # ----------------------------------------------------
        # Transaction amount
        # ----------------------------------------------------

        if field_name == "amount":

            return self.normalize_amount(
                value
            )

        # ----------------------------------------------------
        # Generic strings
        # ----------------------------------------------------

        if isinstance(value, str):

            return self.normalize_text(
                value
            )

        return value

    # ========================================================
    # PHONE
    # ========================================================

    @staticmethod
    def normalize_phone(
        value: Any,
    ) -> str | None:
        """
        Normalize phone numbers.

        Example:

            "+91 98765-43210"
                ↓
            "+919876543210"
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        # Keep leading + and remove formatting characters.
        has_plus = value.startswith("+")

        digits = re.sub(
            r"\D",
            "",
            value,
        )

        if not digits:
            return None

        if has_plus:
            return f"+{digits}"

        return digits

    # ========================================================
    # EMAIL
    # ========================================================

    @staticmethod
    def normalize_email(
        value: Any,
    ) -> str | None:
        """
        Normalize email addresses.
        """

        if value is None:
            return None

        return str(value).strip().lower()

    # ========================================================
    # NAME
    # ========================================================

    @staticmethod
    def normalize_name(
        value: Any,
    ) -> str | None:
        """
        Normalize a person's name while preserving readable
        word boundaries.

        Example:

            "  John   Doe "
                ↓
            "John Doe"
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    # ========================================================
    # TEXT
    # ========================================================

    @staticmethod
    def normalize_text(
        value: Any,
    ) -> str | None:
        """
        Basic text normalization.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    # ========================================================
    # VEHICLE REGISTRATION
    # ========================================================

    @staticmethod
    def normalize_registration_number(
        value: Any,
    ) -> str | None:
        """
        Normalize vehicle registration numbers.

        Example:

            "DL 01 AB 1234"
                ↓
            "DL01AB1234"
        """

        if value is None:
            return None

        value = str(value).upper().strip()

        if not value:
            return None

        return re.sub(
            r"[^A-Z0-9]",
            "",
            value,
        )

    # ========================================================
    # DATETIME
    # ========================================================

    @staticmethod
    def normalize_datetime(
        value: Any,
    ) -> str | None:
        """
        Convert common date formats into ISO 8601 strings.

        Example:

            20/08/2026 10:30
                ↓
            2026-08-20T10:30:00
        """

        if value is None:
            return None

        if isinstance(value, datetime):

            return value.isoformat()

        value = str(value).strip()

        if not value:
            return None

        # ----------------------------------------------------
        # ISO format
        # ----------------------------------------------------

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            return parsed.isoformat()

        except ValueError:
            pass

        # ----------------------------------------------------
        # Common formats
        # ----------------------------------------------------

        formats = (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
        )

        for date_format in formats:

            try:

                parsed = datetime.strptime(
                    value,
                    date_format,
                )

                return parsed.isoformat()

            except ValueError:
                continue

        # ----------------------------------------------------
        # Preserve unknown values rather than destroying data.
        # ----------------------------------------------------

        return value

    # ========================================================
    # GPS COORDINATE
    # ========================================================

    @staticmethod
    def normalize_coordinate(
        value: Any,
    ) -> float | None:
        """
        Convert a coordinate into a float.
        """

        if value is None:
            return None

        try:

            return float(value)

        except (TypeError, ValueError):

            return None

    # ========================================================
    # TRANSACTION AMOUNT
    # ========================================================

    @staticmethod
    def normalize_amount(
        value: Any,
    ) -> float | None:
        """
        Normalize transaction amounts.

        Examples:

            "₹ 10,500.50" → 10500.50

            "$5,000" → 5000.0
        """

        if value is None:
            return None

        if isinstance(value, (int, float)):

            return float(value)

        value = str(value).strip()

        if not value:
            return None

        # Remove currency symbols and thousands separators.
        cleaned = re.sub(
            r"[^0-9.\-]",
            "",
            value,
        )

        if not cleaned:
            return None

        try:

            return float(cleaned)

        except ValueError:

            return None


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def normalize_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize one record.
    """

    normalizer = DataNormalizer()

    return normalizer.normalize_record(
        record
    )


def normalize_records(
    records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize multiple records.
    """

    normalizer = DataNormalizer()

    return normalizer.normalize_records(
        records
    )
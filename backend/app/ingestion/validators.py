from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


# ============================================================
# CONSTANTS
# ============================================================

PHONE_PATTERN = re.compile(
    r"^\+?[0-9][0-9\s\-().]{5,20}$"
)

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

COMMON_DATE_FORMATS = (
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


# ============================================================
# EXCEPTIONS
# ============================================================


class ValidationError(Exception):
    """
    Base exception for ingestion validation errors.
    """

    pass


# ============================================================
# VALIDATION ISSUE
# ============================================================


@dataclass
class ValidationIssue:
    """
    Represents one validation problem.
    """

    record_index: int

    field: str | None

    message: str

    severity: str = "error"


# ============================================================
# VALIDATION RESULT
# ============================================================


@dataclass
class ValidationResult:
    """
    Result returned after validating records.
    """

    valid: bool

    total_records: int

    valid_records: int

    invalid_records: int

    issues: list[ValidationIssue] = field(
        default_factory=list
    )

    valid_data: list[dict[str, Any]] = field(
        default_factory=list
    )

    invalid_data: list[dict[str, Any]] = field(
        default_factory=list
    )

    @property
    def error_count(self) -> int:
        """
        Return the number of error-level issues.
        """

        return sum(
            1
            for issue in self.issues
            if issue.severity == "error"
        )

    @property
    def warning_count(self) -> int:
        """
        Return the number of warning-level issues.
        """

        return sum(
            1
            for issue in self.issues
            if issue.severity == "warning"
        )


# ============================================================
# RECORD VALIDATOR
# ============================================================


class RecordValidator:
    """
    General-purpose validator for parsed ingestion records.

    Performs common validation shared by multiple data sources.
    Source-specific validation can be added later.
    """

    # ========================================================
    # VALIDATE RECORDS
    # ========================================================

    def validate_records(
        self,
        records: Iterable[dict[str, Any]],
        required_fields: list[str] | None = None,
    ) -> ValidationResult:
        """
        Validate a collection of records.
        """

        records = list(records)

        issues: list[ValidationIssue] = []

        valid_data: list[dict[str, Any]] = []

        invalid_data: list[dict[str, Any]] = []

        for index, record in enumerate(records):

            record_issues = self.validate_record(
                record=record,
                record_index=index,
                required_fields=required_fields,
            )

            errors = [
                issue
                for issue in record_issues
                if issue.severity == "error"
            ]

            issues.extend(record_issues)

            if errors:
                invalid_data.append(record)
            else:
                valid_data.append(record)

        return ValidationResult(
            valid=len(invalid_data) == 0,
            total_records=len(records),
            valid_records=len(valid_data),
            invalid_records=len(invalid_data),
            issues=issues,
            valid_data=valid_data,
            invalid_data=invalid_data,
        )

    # ========================================================
    # VALIDATE SINGLE RECORD
    # ========================================================

    def validate_record(
        self,
        record: dict[str, Any],
        record_index: int = 0,
        required_fields: list[str] | None = None,
    ) -> list[ValidationIssue]:
        """
        Validate a single record.
        """

        issues: list[ValidationIssue] = []

        # ----------------------------------------------------
        # Record type
        # ----------------------------------------------------

        if not isinstance(record, dict):

            issues.append(
                ValidationIssue(
                    record_index=record_index,
                    field=None,
                    message="Record must be a dictionary.",
                    severity="error",
                )
            )

            return issues

        # ----------------------------------------------------
        # Empty record
        # ----------------------------------------------------

        if not record:

            issues.append(
                ValidationIssue(
                    record_index=record_index,
                    field=None,
                    message="Record is empty.",
                    severity="error",
                )
            )

            return issues

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        if required_fields:

            for field_name in required_fields:

                if field_name not in record:

                    issues.append(
                        ValidationIssue(
                            record_index=record_index,
                            field=field_name,
                            message=(
                                f"Required field "
                                f"'{field_name}' is missing."
                            ),
                            severity="error",
                        )
                    )

                    continue

                value = record.get(field_name)

                if value is None:

                    issues.append(
                        ValidationIssue(
                            record_index=record_index,
                            field=field_name,
                            message=(
                                f"Required field "
                                f"'{field_name}' is empty."
                            ),
                            severity="error",
                        )
                    )

                elif (
                    isinstance(value, str)
                    and not value.strip()
                ):

                    issues.append(
                        ValidationIssue(
                            record_index=record_index,
                            field=field_name,
                            message=(
                                f"Required field "
                                f"'{field_name}' is blank."
                            ),
                            severity="error",
                        )
                    )

        # ----------------------------------------------------
        # Common fields
        # ----------------------------------------------------

        issues.extend(
            self._validate_common_fields(
                record=record,
                record_index=record_index,
            )
        )

        return issues

    # ========================================================
    # COMMON FIELD VALIDATION
    # ========================================================

    def _validate_common_fields(
        self,
        record: dict[str, Any],
        record_index: int,
    ) -> list[ValidationIssue]:
        """
        Validate commonly encountered ingestion fields.
        """

        issues: list[ValidationIssue] = []

        # ----------------------------------------------------
        # Phone numbers
        # ----------------------------------------------------

        phone_fields = (
            "phone",
            "phone_number",
            "mobile",
            "mobile_number",
            "caller",
            "callee",
        )

        for field_name in phone_fields:

            if field_name not in record:
                continue

            value = record.get(field_name)

            if value is None:
                continue

            if not self.validate_phone(value):

                issues.append(
                    ValidationIssue(
                        record_index=record_index,
                        field=field_name,
                        message="Invalid phone number format.",
                        severity="warning",
                    )
                )

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        email_fields = (
            "email",
            "email_address",
        )

        for field_name in email_fields:

            if field_name not in record:
                continue

            value = record.get(field_name)

            if value is None:
                continue

            if not self.validate_email(value):

                issues.append(
                    ValidationIssue(
                        record_index=record_index,
                        field=field_name,
                        message="Invalid email format.",
                        severity="warning",
                    )
                )

        # ----------------------------------------------------
        # Dates
        # ----------------------------------------------------

        date_fields = (
            "date",
            "datetime",
            "timestamp",
            "incident_date",
            "fir_date",
            "call_date",
            "transaction_date",
            "booking_date",
            "release_date",
            "event_date",
        )

        for field_name in date_fields:

            if field_name not in record:
                continue

            value = record.get(field_name)

            if value is None:
                continue

            if not self.validate_date(value):

                issues.append(
                    ValidationIssue(
                        record_index=record_index,
                        field=field_name,
                        message=(
                            "Invalid or unrecognized "
                            "date format."
                        ),
                        severity="warning",
                    )
                )

        # ----------------------------------------------------
        # Latitude
        # ----------------------------------------------------

        latitude_fields = (
            "latitude",
            "lat",
        )

        for field_name in latitude_fields:

            if field_name not in record:
                continue

            value = record.get(field_name)

            if value is None:
                continue

            if not self.validate_latitude(value):

                issues.append(
                    ValidationIssue(
                        record_index=record_index,
                        field=field_name,
                        message=(
                            "Latitude must be between "
                            "-90 and 90."
                        ),
                        severity="error",
                    )
                )

        # ----------------------------------------------------
        # Longitude
        # ----------------------------------------------------

        longitude_fields = (
            "longitude",
            "lon",
            "lng",
        )

        for field_name in longitude_fields:

            if field_name not in record:
                continue

            value = record.get(field_name)

            if value is None:
                continue

            if not self.validate_longitude(value):

                issues.append(
                    ValidationIssue(
                        record_index=record_index,
                        field=field_name,
                        message=(
                            "Longitude must be between "
                            "-180 and 180."
                        ),
                        severity="error",
                    )
                )

        return issues

    # ========================================================
    # PHONE VALIDATION
    # ========================================================

    @staticmethod
    def validate_phone(
        value: Any,
    ) -> bool:
        """
        Validate basic phone number formatting.

        This does not verify whether the number actually exists.
        """

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()

        if not value:
            return False

        return bool(
            PHONE_PATTERN.fullmatch(value)
        )

    # ========================================================
    # EMAIL VALIDATION
    # ========================================================

    @staticmethod
    def validate_email(
        value: Any,
    ) -> bool:
        """
        Validate basic email syntax.
        """

        if not isinstance(value, str):
            return False

        value = value.strip()

        if not value:
            return False

        return bool(
            EMAIL_PATTERN.fullmatch(value)
        )

    # ========================================================
    # DATE VALIDATION
    # ========================================================

    @staticmethod
    def validate_date(
        value: Any,
    ) -> bool:
        """
        Validate common date and datetime formats.
        """

        if isinstance(value, datetime):
            return True

        if not isinstance(value, str):
            return False

        value = value.strip()

        if not value:
            return False

        # ----------------------------------------------------
        # ISO 8601
        # ----------------------------------------------------

        try:

            datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            return True

        except ValueError:
            pass

        # ----------------------------------------------------
        # Common formats
        # ----------------------------------------------------

        for date_format in COMMON_DATE_FORMATS:

            try:

                datetime.strptime(
                    value,
                    date_format,
                )

                return True

            except ValueError:
                continue

        return False

    # ========================================================
    # LATITUDE
    # ========================================================

    @staticmethod
    def validate_latitude(
        value: Any,
    ) -> bool:
        """
        Validate GPS latitude.
        """

        try:

            latitude = float(value)

        except (TypeError, ValueError):

            return False

        return -90.0 <= latitude <= 90.0

    # ========================================================
    # LONGITUDE
    # ========================================================

    @staticmethod
    def validate_longitude(
        value: Any,
    ) -> bool:
        """
        Validate GPS longitude.
        """

        try:

            longitude = float(value)

        except (TypeError, ValueError):

            return False

        return -180.0 <= longitude <= 180.0


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def validate_records(
    records: Iterable[dict[str, Any]],
    required_fields: list[str] | None = None,
) -> ValidationResult:
    """
    Convenience function for validating multiple records.
    """

    validator = RecordValidator()

    return validator.validate_records(
        records=records,
        required_fields=required_fields,
    )


def validate_record(
    record: dict[str, Any],
    required_fields: list[str] | None = None,
) -> list[ValidationIssue]:
    """
    Convenience function for validating one record.
    """

    validator = RecordValidator()

    return validator.validate_record(
        record=record,
        required_fields=required_fields,
    )
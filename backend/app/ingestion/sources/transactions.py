"""
TRINETRA Transaction Ingestion
==============================

Transaction-specific ingestion and normalization.

Responsibilities
----------------
- Normalize transaction identifiers
- Normalize sender/receiver identifiers
- Normalize amounts and currencies
- Normalize timestamps
- Preserve account/wallet metadata
- Preserve transaction location information
- Prepare records for entity linking and graph construction

This module does NOT:
- determine whether a transaction is criminal
- declare an account/person suspicious
- perform financial surveillance
- access financial institutions
- assign risk scores

Those responsibilities belong to later authorized analytical
stages.
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

TRANSACTION_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Transaction ID
    # --------------------------------------------------------

    "transaction_id": "transaction_id",
    "transaction_no": "transaction_id",
    "transaction_number": "transaction_id",
    "txn_id": "transaction_id",
    "txn_no": "transaction_id",
    "reference_id": "transaction_id",
    "transaction_reference": "transaction_id",

    # --------------------------------------------------------
    # Sender
    # --------------------------------------------------------

    "sender": "sender_identifier",
    "sender_id": "sender_identifier",
    "sender_account": "sender_account",
    "sender_account_number": "sender_account",
    "from_account": "sender_account",
    "source_account": "sender_account",
    "from": "sender_identifier",

    # --------------------------------------------------------
    # Receiver
    # --------------------------------------------------------

    "receiver": "receiver_identifier",
    "receiver_id": "receiver_identifier",
    "receiver_account": "receiver_account",
    "receiver_account_number": "receiver_account",
    "beneficiary_account": "receiver_account",
    "to_account": "receiver_account",
    "destination_account": "receiver_account",
    "to": "receiver_identifier",

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    "transaction_amount": "amount",
    "amount_paid": "amount",
    "amount_transferred": "amount",
    "transfer_amount": "amount",
    "value": "amount",

    # --------------------------------------------------------
    # Currency
    # --------------------------------------------------------

    "currency_code": "currency",
    "currency_type": "currency",
    "curr": "currency",

    # --------------------------------------------------------
    # Date/time
    # --------------------------------------------------------

    "transaction_date": "timestamp",
    "transaction_datetime": "timestamp",
    "transaction_time": "timestamp",
    "date_time": "timestamp",
    "event_time": "timestamp",
    "event_datetime": "timestamp",

    # --------------------------------------------------------
    # Transaction type
    # --------------------------------------------------------

    "txn_type": "transaction_type",
    "type": "transaction_type",
    "transaction_category": "transaction_type",
    "payment_type": "transaction_type",

    # --------------------------------------------------------
    # Account
    # --------------------------------------------------------

    "account": "account_identifier",
    "account_id": "account_identifier",
    "account_number": "account_identifier",

    # --------------------------------------------------------
    # Bank / institution
    # --------------------------------------------------------

    "bank_name": "institution",
    "financial_institution": "institution",
    "institution_name": "institution",

    # --------------------------------------------------------
    # Merchant
    # --------------------------------------------------------

    "merchant_name": "merchant",
    "merchant_id": "merchant",
    "merchant_identifier": "merchant",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "transaction_location": "location",
    "payment_location": "location",
    "place": "location",
    "location_name": "location",

    "lat": "latitude",
    "lng": "longitude",
    "lon": "longitude",

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    "transaction_description": "description",
    "payment_description": "description",
    "narration": "description",
    "remarks": "description",
    "memo": "description",
}


# ============================================================
# TRANSACTION RECORD
# ============================================================


@dataclass
class TransactionRecord:
    """
    Canonical representation of one transaction.

    This is an ingestion-layer object and is intentionally
    independent from the database model.
    """

    transaction_id: str | None = None

    sender_identifier: str | None = None

    receiver_identifier: str | None = None

    sender_account: str | None = None

    receiver_account: str | None = None

    account_identifier: str | None = None

    amount: float | None = None

    currency: str | None = None

    timestamp: str | None = None

    transaction_type: str | None = None

    institution: str | None = None

    merchant: str | None = None

    location: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    description: str | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # GRAPH REPRESENTATION
    # ========================================================

    @property
    def graph_relationship(self) -> dict[str, Any]:
        """
        Return a graph-oriented description of the transaction.

        The graph builder will later decide how this becomes a
        Neo4j node/relationship.
        """

        return {
            "relationship": "TRANSFERRED_TO",
            "source": (
                self.sender_identifier
                or self.sender_account
            ),
            "target": (
                self.receiver_identifier
                or self.receiver_account
            ),
            "transaction_id": self.transaction_id,
            "amount": self.amount,
            "currency": self.currency,
            "timestamp": self.timestamp,
            "transaction_type": self.transaction_type,
            "institution": self.institution,
        }

    # ========================================================
    # DICTIONARY
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the transaction into a dictionary.
        """

        return asdict(self)


# ============================================================
# PROCESSING RESULT
# ============================================================


@dataclass
class TransactionProcessingResult:
    """
    Result returned after processing transaction records.
    """

    records: list[TransactionRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of processed transactions.
        """

        return len(self.records)

    @property
    def has_validation_errors(self) -> bool:
        """
        Check whether processing generated an error-level
        validation issue.
        """

        return any(
            issue.severity == "error"
            for issue in self.validation_issues
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to a serializable dictionary.
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
# TRANSACTION PROCESSOR
# ============================================================


class TransactionProcessor:
    """
    Processes transaction records into a canonical structure.

    Example
    -------

        processor = TransactionProcessor()

        result = processor.process_records(
            records,
            source_file="transactions.csv",
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
    ) -> TransactionProcessingResult:
        """
        Process multiple transaction records.
        """

        records = list(records)

        processed: list[
            TransactionRecord
        ] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_transaction_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            transaction = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(transaction)

        return TransactionProcessingResult(
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
    ) -> TransactionRecord:
        """
        Convert one record into a TransactionRecord.
        """

        normalized = (
            self._normalize_transaction_fields(
                record
            )
        )

        return TransactionRecord(
            transaction_id=self._get_string(
                normalized,
                "transaction_id",
            ),

            sender_identifier=self._get_string(
                normalized,
                "sender_identifier",
            ),

            receiver_identifier=self._get_string(
                normalized,
                "receiver_identifier",
            ),

            sender_account=self._get_string(
                normalized,
                "sender_account",
            ),

            receiver_account=self._get_string(
                normalized,
                "receiver_account",
            ),

            account_identifier=self._get_string(
                normalized,
                "account_identifier",
            ),

            amount=self._normalize_amount(
                normalized.get("amount")
            ),

            currency=self._normalize_currency(
                normalized.get("currency")
            ),

            timestamp=self._get_string(
                normalized,
                "timestamp",
            ),

            transaction_type=self._get_string(
                normalized,
                "transaction_type",
            ),

            institution=self._get_string(
                normalized,
                "institution",
            ),

            merchant=self._get_string(
                normalized,
                "merchant",
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

            description=self._get_string(
                normalized,
                "description",
            ),

            source_file=source_file,

            metadata={
                "source": "transactions",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_transaction_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize generic and transaction-specific field names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                TRANSACTION_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
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
    # AMOUNT
    # ========================================================

    def _normalize_amount(
        self,
        value: Any,
    ) -> float | None:
        """
        Normalize a transaction amount.
        """

        if value is None:
            return None

        if isinstance(value, (int, float)):

            return float(value)

        # Reuse the generic normalizer.
        normalized = (
            self.normalizer.normalize_amount(
                value
            )
        )

        return normalized

    # ========================================================
    # CURRENCY
    # ========================================================

    @staticmethod
    def _normalize_currency(
        value: Any,
    ) -> str | None:
        """
        Normalize currency identifiers.

        Examples:

            "inr" → "INR"
            "usd" → "USD"
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value.upper()

    # ========================================================
    # COORDINATE
    # ========================================================

    @staticmethod
    def _normalize_coordinate(
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
    # STRING HELPER
    # ========================================================

    @staticmethod
    def _get_string(
        record: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Safely retrieve a string value.
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
    def validate_minimum_transaction_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify important transaction fields that are missing.

        Missing fields are reported rather than automatically
        rejecting the record.
        """

        recommended_fields = (
            "transaction_id",
            "amount",
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


def process_transaction_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> TransactionProcessingResult:
    """
    Convenience function for processing transaction records.
    """

    processor = TransactionProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
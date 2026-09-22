"""
TRINETRA Social Media Ingestion
================================

Social-media-specific ingestion and normalization.

Responsibilities
----------------
- Normalize social-media account identifiers
- Normalize platform names
- Preserve post/message text
- Normalize timestamps
- Preserve publicly available/profile metadata
- Extract explicit mentions and hashtags
- Preserve URLs
- Preserve location metadata when present
- Prepare records for NLP and entity linking

This module does NOT:
- access private accounts
- bypass authentication
- scrape protected/private information
- deanonymize users automatically
- determine whether a person is a suspect
- determine guilt
- assign criminal risk

Only data that the investigator/system is authorized to process
should enter this pipeline.
"""

from __future__ import annotations

import re
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

SOCIAL_MEDIA_FIELD_ALIASES: dict[str, str] = {
    # --------------------------------------------------------
    # Record
    # --------------------------------------------------------

    "post_id": "post_id",
    "message_id": "post_id",
    "content_id": "post_id",
    "publication_id": "post_id",

    # --------------------------------------------------------
    # Platform
    # --------------------------------------------------------

    "site": "platform",
    "social_network": "platform",
    "network": "platform",
    "platform_name": "platform",

    # --------------------------------------------------------
    # Account
    # --------------------------------------------------------

    "account": "account_handle",
    "username": "account_handle",
    "user_name": "account_handle",
    "handle": "account_handle",
    "screen_name": "account_handle",

    "account_id": "account_id",
    "user_id": "account_id",
    "profile_id": "account_id",

    # --------------------------------------------------------
    # Display name
    # --------------------------------------------------------

    "user_display_name": "display_name",
    "profile_name": "display_name",
    "account_name": "display_name",

    # --------------------------------------------------------
    # Content
    # --------------------------------------------------------

    "post": "content",
    "post_text": "content",
    "message": "content",
    "text": "content",
    "caption": "content",
    "description": "content",

    # --------------------------------------------------------
    # Date/time
    # --------------------------------------------------------

    "post_date": "timestamp",
    "post_datetime": "timestamp",
    "posted_at": "timestamp",
    "created_at": "timestamp",
    "publication_time": "timestamp",

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    "post_url": "url",
    "profile_url": "profile_url",
    "source_url": "url",
    "permalink": "url",

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    "place": "location",
    "place_name": "location",
    "location_name": "location",
    "post_location": "location",

    "lat": "latitude",
    "lng": "longitude",
    "lon": "longitude",

    # --------------------------------------------------------
    # Engagement
    # --------------------------------------------------------

    "like_count": "likes",
    "likes_count": "likes",

    "comment_count": "comments",
    "comments_count": "comments",

    "share_count": "shares",
    "shares_count": "shares",

    "retweet_count": "shares",

    # --------------------------------------------------------
    # Related account
    # --------------------------------------------------------

    "mentioned_user": "mentions",
    "mentioned_users": "mentions",
    "tagged_users": "mentions",

    # --------------------------------------------------------
    # Tags
    # --------------------------------------------------------

    "tag": "hashtags",
    "tags": "hashtags",
    "hash_tags": "hashtags",

    # --------------------------------------------------------
    # Media
    # --------------------------------------------------------

    "media_url": "media_urls",
    "image_url": "media_urls",
    "video_url": "media_urls",
}


# ============================================================
# SOCIAL MEDIA RECORD
# ============================================================


@dataclass
class SocialMediaRecord:
    """
    Canonical representation of a social-media record.

    The record is intentionally independent from the database
    layer.
    """

    post_id: str | None = None

    platform: str | None = None

    account_id: str | None = None

    account_handle: str | None = None

    display_name: str | None = None

    content: str | None = None

    timestamp: str | None = None

    url: str | None = None

    profile_url: str | None = None

    location: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    mentions: list[str] = field(
        default_factory=list
    )

    hashtags: list[str] = field(
        default_factory=list
    )

    media_urls: list[str] = field(
        default_factory=list
    )

    likes: int | None = None

    comments: int | None = None

    shares: int | None = None

    source_file: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # NLP TEXT
    # ========================================================

    @property
    def nlp_text(self) -> str:
        """
        Return text suitable for the NLP pipeline.

        The NLP layer can later extract entities such as:
        people, organizations, locations, vehicles, dates,
        phone numbers, case references, etc.
        """

        parts: list[str] = []

        if self.display_name:
            parts.append(
                f"Display Name: {self.display_name}"
            )

        if self.account_handle:
            parts.append(
                f"Account: {self.account_handle}"
            )

        if self.content:
            parts.append(
                f"Content: {self.content}"
            )

        if self.location:
            parts.append(
                f"Location: {self.location}"
            )

        if self.hashtags:
            parts.append(
                "Hashtags: "
                + ", ".join(self.hashtags)
            )

        if self.mentions:
            parts.append(
                "Mentions: "
                + ", ".join(self.mentions)
            )

        return "\n".join(parts)

    # ========================================================
    # GRAPH REPRESENTATION
    # ========================================================

    @property
    def graph_entity(self) -> dict[str, Any]:
        """
        Return a graph-oriented representation.

        The graph builder is responsible for deciding which
        nodes and relationships should actually be created.
        """

        return {
            "entity_type": "SOCIAL_POST",
            "post_id": self.post_id,
            "platform": self.platform,
            "account_id": self.account_id,
            "account_handle": self.account_handle,
            "timestamp": self.timestamp,
            "url": self.url,
        }

    # ========================================================
    # DICTIONARY
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the record into a dictionary.
        """

        return asdict(self)


# ============================================================
# PROCESSING RESULT
# ============================================================


@dataclass
class SocialMediaProcessingResult:
    """
    Result returned after social-media processing.
    """

    records: list[SocialMediaRecord]

    validation_issues: list[ValidationIssue] = field(
        default_factory=list
    )

    source_file: str | None = None

    @property
    def count(self) -> int:
        """
        Number of processed records.
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
        Convert result into a serializable dictionary.
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
# SOCIAL MEDIA PROCESSOR
# ============================================================


class SocialMediaProcessor:
    """
    Processes authorized social-media records.

    Example
    -------

        processor = SocialMediaProcessor()

        result = processor.process_records(
            records,
            source_file="social_media.json",
        )
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
    ) -> SocialMediaProcessingResult:
        """
        Process multiple social-media records.
        """

        records = list(records)

        processed: list[
            SocialMediaRecord
        ] = []

        validation_issues: list[
            ValidationIssue
        ] = []

        for index, record in enumerate(records):

            normalized = (
                self._normalize_social_fields(
                    record
                )
            )

            issues = self.validator.validate_record(
                normalized,
                record_index=index,
                required_fields=[],
            )

            validation_issues.extend(issues)

            social_record = self.process_record(
                normalized,
                source_file=source_file,
            )

            processed.append(
                social_record
            )

        return SocialMediaProcessingResult(
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
    ) -> SocialMediaRecord:
        """
        Convert one generic record into a
        SocialMediaRecord.
        """

        normalized = (
            self._normalize_social_fields(
                record
            )
        )

        content = self._get_string(
            normalized,
            "content",
        )

        # ----------------------------------------------------
        # If mentions/hashtags were not explicitly provided,
        # derive them from the supplied content.
        # ----------------------------------------------------

        mentions = self._normalize_list(
            normalized.get("mentions")
        )

        hashtags = self._normalize_list(
            normalized.get("hashtags")
        )

        if content:

            detected_mentions = (
                self.extract_mentions(content)
            )

            detected_hashtags = (
                self.extract_hashtags(content)
            )

            mentions = self._merge_unique(
                mentions,
                detected_mentions,
            )

            hashtags = self._merge_unique(
                hashtags,
                detected_hashtags,
            )

        return SocialMediaRecord(
            post_id=self._get_string(
                normalized,
                "post_id",
            ),

            platform=self._normalize_platform(
                normalized.get("platform")
            ),

            account_id=self._get_string(
                normalized,
                "account_id",
            ),

            account_handle=self._normalize_handle(
                normalized.get("account_handle")
            ),

            display_name=self._get_string(
                normalized,
                "display_name",
            ),

            content=content,

            timestamp=self._get_string(
                normalized,
                "timestamp",
            ),

            url=self._get_string(
                normalized,
                "url",
            ),

            profile_url=self._get_string(
                normalized,
                "profile_url",
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

            mentions=mentions,

            hashtags=hashtags,

            media_urls=self._normalize_list(
                normalized.get("media_urls")
            ),

            likes=self._normalize_integer(
                normalized.get("likes")
            ),

            comments=self._normalize_integer(
                normalized.get("comments")
            ),

            shares=self._normalize_integer(
                normalized.get("shares")
            ),

            source_file=source_file,

            metadata={
                "source": "social_media",
                "original_fields": list(
                    record.keys()
                ),
            },
        )

    # ========================================================
    # FIELD NORMALIZATION
    # ========================================================

    def _normalize_social_fields(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert source-specific social-media field names into
        canonical names.
        """

        normalized: dict[str, Any] = {}

        for key, value in record.items():

            generic_key = (
                self.normalizer.normalize_field_name(
                    key
                )
            )

            canonical_key = (
                SOCIAL_MEDIA_FIELD_ALIASES.get(
                    generic_key,
                    generic_key,
                )
            )

            # ------------------------------------------------
            # Datetime
            # ------------------------------------------------

            if canonical_key == "timestamp":

                normalized_value = (
                    self.normalizer.normalize_datetime(
                        value
                    )
                )

            # ------------------------------------------------
            # Coordinates
            # ------------------------------------------------

            elif canonical_key in {
                "latitude",
                "longitude",
            }:

                normalized_value = (
                    self._normalize_coordinate(
                        value
                    )
                )

            # ------------------------------------------------
            # Lists
            # ------------------------------------------------

            elif canonical_key in {
                "mentions",
                "hashtags",
                "media_urls",
            }:

                normalized_value = (
                    self._normalize_list(
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
    # PLATFORM
    # ========================================================

    @staticmethod
    def _normalize_platform(
        value: Any,
    ) -> str | None:
        """
        Normalize platform names.

        The exact source name is retained rather than attempting
        to infer the platform from a username.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value.lower()

    # ========================================================
    # ACCOUNT HANDLE
    # ========================================================

    @staticmethod
    def _normalize_handle(
        value: Any,
    ) -> str | None:
        """
        Normalize a social-media handle.

        Example:

            "@ExampleUser" → "ExampleUser"
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if value.startswith("@"):

            value = value[1:]

        return value

    # ========================================================
    # MENTIONS
    # ========================================================

    @staticmethod
    def extract_mentions(
        text: str,
    ) -> list[str]:
        """
        Extract explicit @mentions from supplied text.

        This is simple lexical extraction. It does not identify
        the real-world person behind the account.
        """

        if not text:
            return []

        matches = re.findall(
            r"(?<![\w])@([A-Za-z0-9_.-]+)",
            text,
        )

        return SocialMediaProcessor._merge_unique(
            [],
            matches,
        )

    # ========================================================
    # HASHTAGS
    # ========================================================

    @staticmethod
    def extract_hashtags(
        text: str,
    ) -> list[str]:
        """
        Extract explicit hashtags.

        This is not semantic classification.
        """

        if not text:
            return []

        matches = re.findall(
            r"(?<![\w])#([A-Za-z0-9_]+)",
            text,
        )

        return SocialMediaProcessor._merge_unique(
            [],
            matches,
        )

    # ========================================================
    # LIST NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_list(
        value: Any,
    ) -> list[str]:
        """
        Normalize list-like input.

        Supports:

            ["a", "b"]

        and:

            "a,b"

        and:

            "a"
        """

        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):

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

            if item.startswith("@"):

                item = item[1:]

            if item.startswith("#"):

                item = item[1:]

            if item not in result:

                result.append(item)

        return result

    # ========================================================
    # UNIQUE MERGE
    # ========================================================

    @staticmethod
    def _merge_unique(
        first: list[str],
        second: list[str],
    ) -> list[str]:
        """
        Merge two lists without duplicates.
        """

        result: list[str] = []

        for item in [*first, *second]:

            if item not in result:

                result.append(item)

        return result

    # ========================================================
    # INTEGER
    # ========================================================

    @staticmethod
    def _normalize_integer(
        value: Any,
    ) -> int | None:
        """
        Normalize engagement counts.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:

            return int(float(value))

        except (TypeError, ValueError):

            return None

    # ========================================================
    # COORDINATE
    # ========================================================

    @staticmethod
    def _normalize_coordinate(
        value: Any,
    ) -> float | None:
        """
        Normalize latitude/longitude values.
        """

        if value is None:
            return None

        try:

            return float(value)

        except (TypeError, ValueError):

            return None

    # ========================================================
    # STRING
    # ========================================================

    @staticmethod
    def _get_string(
        record: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Safely retrieve a string.
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
    def validate_minimum_social_fields(
        record: dict[str, Any],
    ) -> list[str]:
        """
        Identify recommended fields that are missing.

        Missing fields are reported rather than automatically
        rejecting the record.
        """

        recommended_fields = (
            "platform",
            "content",
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


def process_social_media_records(
    records: Iterable[dict[str, Any]],
    source_file: str | None = None,
) -> SocialMediaProcessingResult:
    """
    Convenience function for processing social-media records.
    """

    processor = SocialMediaProcessor()

    return processor.process_records(
        records=records,
        source_file=source_file,
    )
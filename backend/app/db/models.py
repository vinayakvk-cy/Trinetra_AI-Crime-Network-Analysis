"""
TRINETRA Database Models Foundation
====================================

Contains shared SQLAlchemy ORM utilities and mixins.

Domain-specific models are defined separately under:

    app/models/

Examples:

    app/models/case.py
    app/models/entity.py
    app/models/evidence.py
    app/models/investigation.py

This file provides reusable database model components.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ============================================================
# TIMESTAMP MIXIN
# ============================================================

class TimestampMixin:
    """
    Adds creation and update timestamps to a database model.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ============================================================
# ID MIXIN
# ============================================================

class IDMixin:
    """
    Provides a standard integer primary key.

    Individual domain models can use this when an integer
    database ID is appropriate.
    """

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )


# ============================================================
# METADATA MIXIN
# ============================================================

class MetadataMixin:
    """
    Provides a JSON metadata field.

    Useful for storing additional structured information
    that may vary between different data sources.

    Example:

        {
            "source": "fir",
            "source_file": "fir_001.json",
            "confidence": 0.91
        }
    """

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )


# ============================================================
# SOFT DELETE MIXIN
# ============================================================

class SoftDeleteMixin:
    """
    Provides soft-delete support.

    Records are not physically removed from the database.
    Instead, deleted_at is populated.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        """
        Return whether this record has been soft deleted.
        """

        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        """
        Mark the record as deleted.
        """

        self.deleted_at = datetime.now(
            timezone.utc
        )

    def restore(self) -> None:
        """
        Restore a soft-deleted record.
        """

        self.deleted_at = None


# ============================================================
# AUDIT MIXIN
# ============================================================

class AuditMixin:
    """
    Stores basic audit information.

    This becomes useful when multiple investigators or
    analysts interact with the same case.
    """

    created_by: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    updated_by: Mapped[str | None] = mapped_column(
        nullable=True,
    )


# ============================================================
# BASE APPLICATION MODEL
# ============================================================

class BaseModel(
    Base,
    IDMixin,
    TimestampMixin,
):
    """
    Common base class for TRINETRA database models.

    Domain models can inherit from this class when they need:

        - Integer ID
        - created_at
        - updated_at
    """

    __abstract__ = True


# ============================================================
# FULL APPLICATION MODEL
# ============================================================

class FullBaseModel(
    Base,
    IDMixin,
    TimestampMixin,
    MetadataMixin,
    SoftDeleteMixin,
    AuditMixin,
):
    """
    Extended base model containing common application fields.

    Useful for entities such as:

        - Cases
        - Investigations
        - Evidence
        - Intelligence records
    """

    __abstract__ = True
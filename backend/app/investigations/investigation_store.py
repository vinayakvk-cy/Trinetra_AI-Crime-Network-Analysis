"""
TRINETRA Investigation Store
============================

Persistence layer for investigation records.

Responsibilities
----------------
- Create investigations
- Retrieve investigations
- Update investigation status/details
- List investigations
- Delete investigations
- Keep database access separate from API routes

This module does NOT:
- Perform NLP
- Build the graph
- Run analytics
- Generate reports
- Manage individual investigation tasks
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.models import investigation


class InvestigationStore:
    """
    Database-backed store for investigations.
    """

    VALID_STATUSES = {
        "open",
        "active",
        "paused",
        "completed",
        "archived",
    }

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    # ========================================================
    # CREATE
    # ========================================================

    def create(
        self,
        case_id: int,
        title: str,
        description: str | None = None,
        status: str = "open",
        metadata: dict[str, Any] | None = None,
    ) -> Investigation:
        """
        Create a new investigation.
        """

        self._validate_status(status)

        if not title or not title.strip():
            raise ValueError(
                "Investigation title cannot be empty."
            )

        investigation = Investigation(
            case_id=case_id,
            title=title.strip(),
            description=description,
            status=status,
            metadata=metadata or {},
        )

        self.session.add(investigation)
        self.session.commit()
        self.session.refresh(investigation)

        return investigation

    # ========================================================
    # GET BY ID
    # ========================================================

    def get_by_id(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Retrieve an investigation by primary key.
        """

        statement = select(
            Investigation
        ).where(
            Investigation.id
            == investigation_id
        )

        return self.session.scalar(
            statement
        )

    # ========================================================
    # GET BY CASE
    # ========================================================

    def get_by_case(
        self,
        case_id: int,
    ) -> list[Investigation]:
        """
        Retrieve all investigations belonging to a case.
        """

        statement = (
            select(Investigation)
            .where(
                Investigation.case_id
                == case_id
            )
            .order_by(
                Investigation.created_at.desc()
            )
        )

        return list(
            self.session.scalars(
                statement
            ).all()
        )

    # ========================================================
    # LIST
    # ========================================================

    def list(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Investigation]:
        """
        List investigations with optional status filtering.
        """

        if status is not None:
            self._validate_status(status)

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        if limit > 500:
            raise ValueError(
                "Limit cannot exceed 500."
            )

        if offset < 0:
            raise ValueError(
                "Offset cannot be negative."
            )

        statement = select(
            Investigation
        )

        if status is not None:
            statement = statement.where(
                Investigation.status
                == status
            )

        statement = (
            statement
            .order_by(
                Investigation.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.session.scalars(
                statement
            ).all()
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        investigation_id: int,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Investigation | None:
        """
        Update an existing investigation.
        """

        investigation = self.get_by_id(
            investigation_id
        )

        if investigation is None:
            return None

        if title is not None:

            if not title.strip():
                raise ValueError(
                    "Investigation title cannot be empty."
                )

            investigation.title = (
                title.strip()
            )

        if description is not None:
            investigation.description = (
                description
            )

        if status is not None:

            self._validate_status(
                status
            )

            investigation.status = status

        if metadata is not None:
         investigation.metadata_json = (
        metadata
    )

        self._touch_updated_at(
            investigation
        )

        self.session.commit()
        self.session.refresh(investigation)

        return investigation

    # ========================================================
    # STATUS
    # ========================================================

    def update_status(
        self,
        investigation_id: int,
        status: str,
    ) -> Investigation | None:
        """
        Update only the investigation status.
        """

        self._validate_status(
            status
        )

        investigation = self.get_by_id(
            investigation_id
        )

        if investigation is None:
            return None

        investigation.status = status

        self._touch_updated_at(
            investigation
        )

        self.session.commit()
        self.session.refresh(investigation)

        return investigation

    # ========================================================
    # METADATA
    # ========================================================

    def update_metadata(
        self,
        investigation_id: int,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> Investigation | None:
        """
        Update investigation metadata.

        If merge=True, existing metadata is preserved and
        the supplied values overwrite matching keys.
        """

        investigation = self.get_by_id(
            investigation_id
        )

        if investigation is None:
            return None

        if merge:

            current = (
                investigation.metadata_json
                or {}
            )

            updated = {
                **current,
                **metadata,
            }

        else:
            updated = metadata

        investigation.metadata_json = updated

        self._touch_updated_at(
            investigation
        )

        self.session.commit()
        self.session.refresh(investigation)

        return investigation

    # ========================================================
    # DELETE
    # ========================================================

    def delete(
        self,
        investigation_id: int,
    ) -> bool:
        """
        Delete an investigation.

        Returns True if an investigation was deleted.
        """

        investigation = self.get_by_id(
            investigation_id
        )

        if investigation is None:
            return False

        self.session.delete(
            investigation
        )

        self.session.commit()

        return True

    # ========================================================
    # EXISTS
    # ========================================================

    def exists(
        self,
        investigation_id: int,
    ) -> bool:
        """
        Check whether an investigation exists.
        """

        return (
            self.get_by_id(
                investigation_id
            )
            is not None
        )

    # ========================================================
    # COUNT
    # ========================================================

    def count(
        self,
        status: str | None = None,
    ) -> int:
        """
        Count investigations.

        Uses the ORM query rather than maintaining a separate
        counter.
        """

        investigations = self.list(
            status=status,
            limit=500,
            offset=0,
        )

        return len(investigations)

    # ========================================================
    # COMPLETE
    # ========================================================

    def complete(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Mark an investigation as completed.
        """

        return self.update_status(
            investigation_id=investigation_id,
            status="completed",
        )

    # ========================================================
    # ARCHIVE
    # ========================================================

    def archive(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Mark an investigation as archived.
        """

        return self.update_status(
            investigation_id=investigation_id,
            status="archived",
        )

    # ========================================================
    # REOPEN
    # ========================================================

    def reopen(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Reopen a completed or paused investigation.
        """

        investigation = self.get_by_id(
            investigation_id
        )

        if investigation is None:
            return None

        if investigation.status == "archived":
            raise ValueError(
                "Archived investigations cannot be reopened "
                "directly."
            )

        return self.update_status(
            investigation_id=investigation_id,
            status="active",
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    @classmethod
    def _validate_status(
        cls,
        status: str,
    ) -> None:
        """
        Validate investigation status.
        """

        if status not in cls.VALID_STATUSES:
            allowed = ", ".join(
                sorted(
                    cls.VALID_STATUSES
                )
            )

            raise ValueError(
                f"Invalid investigation status "
                f"'{status}'. Allowed values: {allowed}."
            )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    @staticmethod
    def _touch_updated_at(
        investigation: Investigation,
    ) -> None:
        """
        Update the modification timestamp if the model
        provides an updated_at field.
        """

        if hasattr(
            investigation,
            "updated_at",
        ):
            investigation.updated_at = (
                datetime.now(
                    timezone.utc
                )
            )
"""
TRINETRA Investigation Action Manager
=====================================

Manages tasks/actions associated with investigations.

Responsibilities
----------------
- Create investigation actions
- Retrieve actions
- Update action status
- Assign actions
- Track action results
- Track action timestamps
- List pending/completed actions

This module does NOT:
- Perform the actual graph analysis
- Run NLP
- Build Neo4j graphs
- Generate reports
- Determine guilt
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation


# ============================================================
# ACTION DATA
# ============================================================


class InvestigationActionManager:
    """
    Manages investigation actions.

    Action records are stored inside the investigation's
    metadata until a dedicated InvestigationAction database
    model is introduced.

    Expected metadata structure:

        {
            "actions": [
                {
                    "id": 1,
                    "title": "...",
                    "description": "...",
                    "action_type": "...",
                    "status": "...",
                    "priority": "...",
                    "assigned_to": "...",
                    "result": {},
                    "created_at": "...",
                    "updated_at": "..."
                }
            ]
        }
    """

    VALID_STATUSES = {
        "pending",
        "in_progress",
        "completed",
        "cancelled",
        "blocked",
    }

    VALID_PRIORITIES = {
        "low",
        "medium",
        "high",
        "critical",
    }

    VALID_ACTION_TYPES = {
        "review_evidence",
        "inspect_entity",
        "verify_relationship",
        "run_graph_query",
        "run_analysis",
        "collect_information",
        "review_report",
        "investigator_note",
        "other",
    }

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    # ========================================================
    # CREATE ACTION
    # ========================================================

    def create_action(
        self,
        investigation_id: int,
        title: str,
        description: str | None = None,
        action_type: str = "other",
        priority: str = "medium",
        assigned_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new action for an investigation.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        self._validate_action_type(
            action_type
        )

        self._validate_priority(
            priority
        )

        if not title or not title.strip():
            raise ValueError(
                "Action title cannot be empty."
            )

        actions = self._get_actions(
            investigation
        )

        action_id = self._next_action_id(
            actions
        )

        now = self._now()

        action = {
            "id": action_id,
            "title": title.strip(),
            "description": description,
            "action_type": action_type,
            "status": "pending",
            "priority": priority,
            "assigned_to": assigned_to,
            "result": None,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
        }

        actions.append(action)

        self._save_actions(
            investigation,
            actions,
        )

        return action

    # ========================================================
    # GET ACTION
    # ========================================================

    def get_action(
        self,
        investigation_id: int,
        action_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve one action.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return None

        actions = self._get_actions(
            investigation
        )

        for action in actions:

            if action.get("id") == action_id:
                return action

        return None

    # ========================================================
    # LIST ACTIONS
    # ========================================================

    def list_actions(
        self,
        investigation_id: int,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List actions belonging to an investigation.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return []

        if status is not None:
            self._validate_status(
                status
            )

        if priority is not None:
            self._validate_priority(
                priority
            )

        actions = self._get_actions(
            investigation
        )

        if status is not None:
            actions = [
                action
                for action in actions
                if action.get("status")
                == status
            ]

        if priority is not None:
            actions = [
                action
                for action in actions
                if action.get("priority")
                == priority
            ]

        return sorted(
            actions,
            key=self._action_sort_key,
        )

    # ========================================================
    # START ACTION
    # ========================================================

    def start_action(
        self,
        investigation_id: int,
        action_id: int,
    ) -> dict[str, Any] | None:
        """
        Move an action from pending to in_progress.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        current_status = action.get(
            "status"
        )

        if current_status in {
            "completed",
            "cancelled",
        }:
            raise ValueError(
                f"Cannot start an action with "
                f"status '{current_status}'."
            )

        now = self._now()

        action["status"] = "in_progress"
        action["started_at"] = (
            action.get("started_at")
            or now
        )
        action["updated_at"] = now

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # COMPLETE ACTION
    # ========================================================

    def complete_action(
        self,
        investigation_id: int,
        action_id: int,
        result: Any = None,
    ) -> dict[str, Any] | None:
        """
        Mark an action as completed and optionally store
        its result.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        if action.get("status") == "cancelled":
            raise ValueError(
                "Cancelled actions cannot be completed."
            )

        now = self._now()

        action["status"] = "completed"
        action["result"] = result
        action["completed_at"] = now
        action["updated_at"] = now

        if not action.get("started_at"):
            action["started_at"] = now

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # CANCEL ACTION
    # ========================================================

    def cancel_action(
        self,
        investigation_id: int,
        action_id: int,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Cancel an action.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        if action.get("status") == "completed":
            raise ValueError(
                "Completed actions cannot be cancelled."
            )

        now = self._now()

        action["status"] = "cancelled"
        action["updated_at"] = now

        if reason:
            action["metadata"] = {
                **(
                    action.get("metadata")
                    or {}
                ),
                "cancellation_reason": reason,
            }

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # BLOCK ACTION
    # ========================================================

    def block_action(
        self,
        investigation_id: int,
        action_id: int,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Mark an action as blocked.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        if action.get("status") in {
            "completed",
            "cancelled",
        }:
            raise ValueError(
                "Completed or cancelled actions "
                "cannot be blocked."
            )

        now = self._now()

        action["status"] = "blocked"
        action["updated_at"] = now

        if reason:
            action["metadata"] = {
                **(
                    action.get("metadata")
                    or {}
                ),
                "blocked_reason": reason,
            }

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # REOPEN ACTION
    # ========================================================

    def reopen_action(
        self,
        investigation_id: int,
        action_id: int,
    ) -> dict[str, Any] | None:
        """
        Return a blocked or cancelled action to pending.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        if action.get("status") == "completed":
            raise ValueError(
                "Completed actions should not be reopened."
            )

        action["status"] = "pending"
        action["updated_at"] = self._now()

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # ASSIGN ACTION
    # ========================================================

    def assign_action(
        self,
        investigation_id: int,
        action_id: int,
        assigned_to: str | None,
    ) -> dict[str, Any] | None:
        """
        Assign or unassign an action.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        action["assigned_to"] = (
            assigned_to
        )

        action["updated_at"] = self._now()

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # UPDATE RESULT
    # ========================================================

    def update_result(
        self,
        investigation_id: int,
        action_id: int,
        result: Any,
    ) -> dict[str, Any] | None:
        """
        Store or replace the result associated with an action.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        action["result"] = result
        action["updated_at"] = self._now()

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # UPDATE METADATA
    # ========================================================

    def update_metadata(
        self,
        investigation_id: int,
        action_id: int,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> dict[str, Any] | None:
        """
        Update action metadata.
        """

        action = self.get_action(
            investigation_id,
            action_id,
        )

        if action is None:
            return None

        if merge:
            action["metadata"] = {
                **(
                    action.get("metadata")
                    or {}
                ),
                **metadata,
            }
        else:
            action["metadata"] = metadata

        action["updated_at"] = self._now()

        self._persist_action(
            investigation_id,
            action,
        )

        return action

    # ========================================================
    # SUMMARY
    # ========================================================

    def summary(
        self,
        investigation_id: int,
    ) -> dict[str, Any]:
        """
        Return an action summary for an investigation.
        """

        actions = self.list_actions(
            investigation_id
        )

        status_counts = {
            status: 0
            for status in self.VALID_STATUSES
        }

        priority_counts = {
            priority: 0
            for priority in self.VALID_PRIORITIES
        }

        for action in actions:

            status = action.get(
                "status"
            )

            priority = action.get(
                "priority"
            )

            if status in status_counts:
                status_counts[status] += 1

            if priority in priority_counts:
                priority_counts[priority] += 1

        return {
            "investigation_id": investigation_id,
            "total": len(actions),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "pending": status_counts["pending"],
            "in_progress": status_counts[
                "in_progress"
            ],
            "completed": status_counts[
                "completed"
            ],
            "blocked": status_counts[
                "blocked"
            ],
            "cancelled": status_counts[
                "cancelled"
            ],
        }

    # ========================================================
    # INTERNAL: GET INVESTIGATION
    # ========================================================

    def _get_investigation(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Retrieve investigation using the existing model.
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
    # INTERNAL: GET ACTIONS
    # ========================================================

    @staticmethod
    def _get_actions(
        investigation: Investigation,
    ) -> list[dict[str, Any]]:
        """
        Read actions from investigation metadata.
        """

        metadata = (
            investigation.metadata_json
            or {}
        )

        actions = metadata.get(
            "actions",
            [],
        )

        if not isinstance(
            actions,
            list,
        ):
            return []

        return actions

    # ========================================================
    # INTERNAL: SAVE ACTIONS
    # ========================================================

    def _save_actions(
        self,
        investigation: Investigation,
        actions: list[dict[str, Any]],
    ) -> None:
        """
        Persist actions inside investigation metadata.
        """

        current_metadata = (
            investigation.metadata_json
            or {}
        )

        investigation.metadata_json = {
            **current_metadata,
            "actions": actions,
        }

        self._touch_updated_at(
            investigation
        )

        self.session.commit()
        self.session.refresh(
            investigation
        )

    # ========================================================
    # INTERNAL: PERSIST ONE ACTION
    # ========================================================

    def _persist_action(
        self,
        investigation_id: int,
        updated_action: dict[str, Any],
    ) -> None:
        """
        Replace an action and persist the investigation.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        actions = self._get_actions(
            investigation
        )

        action_id = updated_action.get(
            "id"
        )

        found = False

        for index, action in enumerate(
            actions
        ):

            if action.get("id") == action_id:

                actions[index] = (
                    updated_action
                )

                found = True
                break

        if not found:
            raise ValueError(
                "Investigation action not found."
            )

        self._save_actions(
            investigation,
            actions,
        )

    # ========================================================
    # INTERNAL: NEXT ID
    # ========================================================

    @staticmethod
    def _next_action_id(
        actions: list[dict[str, Any]],
    ) -> int:
        """
        Generate the next action ID within an investigation.
        """

        if not actions:
            return 1

        existing_ids = [
            int(action.get("id", 0))
            for action in actions
            if action.get("id") is not None
        ]

        if not existing_ids:
            return 1

        return max(existing_ids) + 1

    # ========================================================
    # INTERNAL: SORT
    # ========================================================

    @staticmethod
    def _action_sort_key(
        action: dict[str, Any],
    ) -> tuple[int, str]:
        """
        Sort actions by priority and then title.
        """

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        priority = priority_order.get(
            action.get("priority"),
            99,
        )

        title = str(
            action.get(
                "title",
                "",
            )
        ).lower()

        return (
            priority,
            title,
        )

    # ========================================================
    # INTERNAL: VALIDATION
    # ========================================================

    @classmethod
    def _validate_status(
        cls,
        status: str,
    ) -> None:
        """
        Validate action status.
        """

        if status not in cls.VALID_STATUSES:
            raise ValueError(
                f"Invalid action status '{status}'. "
                f"Allowed values: "
                f"{', '.join(sorted(cls.VALID_STATUSES))}."
            )

    @classmethod
    def _validate_priority(
        cls,
        priority: str,
    ) -> None:
        """
        Validate action priority.
        """

        if priority not in cls.VALID_PRIORITIES:
            raise ValueError(
                f"Invalid action priority '{priority}'. "
                f"Allowed values: "
                f"{', '.join(sorted(cls.VALID_PRIORITIES))}."
            )

    @classmethod
    def _validate_action_type(
        cls,
        action_type: str,
    ) -> None:
        """
        Validate action type.
        """

        if action_type not in cls.VALID_ACTION_TYPES:
            raise ValueError(
                f"Invalid action type '{action_type}'. "
                f"Allowed values: "
                f"{', '.join(sorted(cls.VALID_ACTION_TYPES))}."
            )

    # ========================================================
    # INTERNAL: TIMESTAMP
    # ========================================================

    @staticmethod
    def _now() -> str:
        """
        Return an ISO-8601 UTC timestamp.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _touch_updated_at(
        investigation: Investigation,
    ) -> None:
        """
        Update model timestamp when supported.
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

ActionManager = InvestigationActionManager
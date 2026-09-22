"""
TRINETRA Case Memory
====================

Case-specific investigation memory.

Responsibilities
----------------
- Store investigation findings
- Store observations and notes
- Store decisions/context
- Retrieve relevant case memory
- Maintain chronological memory
- Support simple keyword search

Memory is stored inside the existing Investigation.metadata
JSON structure because the current architecture does not define
a separate CaseMemory database model.

This module does NOT:
- Perform NLP
- Modify the Neo4j graph
- Determine guilt
- Generate final reports
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation


class CaseMemory:
    """
    Manages persistent investigation memory.

    Expected metadata structure:

        {
            "memory": [
                {
                    "id": 1,
                    "type": "finding",
                    "title": "...",
                    "content": "...",
                    "source": "...",
                    "created_at": "...",
                    "metadata": {}
                }
            ]
        }
    """

    VALID_MEMORY_TYPES = {
        "finding",
        "observation",
        "note",
        "decision",
        "evidence_review",
        "entity_review",
        "relationship_review",
        "analysis",
        "system",
    }

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    # ========================================================
    # ADD MEMORY
    # ========================================================

    def add(
        self,
        investigation_id: int,
        content: str,
        memory_type: str = "note",
        title: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add a memory entry to an investigation.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        self._validate_memory_type(
            memory_type
        )

        if not content or not content.strip():
            raise ValueError(
                "Memory content cannot be empty."
            )

        memory = self._get_memory(
            investigation
        )

        memory_id = self._next_memory_id(
            memory
        )

        now = self._now()

        entry = {
            "id": memory_id,
            "type": memory_type,
            "title": (
                title.strip()
                if title
                else None
            ),
            "content": content.strip(),
            "source": source,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {},
        }

        memory.append(entry)

        self._save_memory(
            investigation,
            memory,
        )

        return entry

    # ========================================================
    # GET MEMORY
    # ========================================================

    def get(
        self,
        investigation_id: int,
        memory_id: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve one memory entry.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return None

        memory = self._get_memory(
            investigation
        )

        for entry in memory:

            if entry.get("id") == memory_id:
                return entry

        return None

    # ========================================================
    # LIST MEMORY
    # ========================================================

    def list(
        self,
        investigation_id: int,
        memory_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List memory entries.

        Newest entries are returned first.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return []

        if memory_type is not None:
            self._validate_memory_type(
                memory_type
            )

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        if limit > 500:
            raise ValueError(
                "Limit cannot exceed 500."
            )

        memory = self._get_memory(
            investigation
        )

        if memory_type is not None:

            memory = [
                entry
                for entry in memory
                if entry.get("type")
                == memory_type
            ]

        memory = sorted(
            memory,
            key=lambda entry: entry.get(
                "created_at",
                "",
            ),
            reverse=True,
        )

        return memory[:limit]

    # ========================================================
    # SEARCH MEMORY
    # ========================================================

    def search(
        self,
        investigation_id: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search case memory using simple case-insensitive
        keyword matching.

        This is intentionally lightweight. A future version
        can use embeddings/vector search if required.
        """

        if not query or not query.strip():
            return []

        if limit < 1:
            raise ValueError(
                "Limit must be at least 1."
            )

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return []

        search_text = query.strip().lower()

        memory = self._get_memory(
            investigation
        )

        matches: list[
            tuple[int, dict[str, Any]]
        ] = []

        for entry in memory:

            title = str(
                entry.get(
                    "title",
                    "",
                )
            ).lower()

            content = str(
                entry.get(
                    "content",
                    "",
                )
            ).lower()

            source = str(
                entry.get(
                    "source",
                    "",
                )
            ).lower()

            searchable = (
                f"{title} "
                f"{content} "
                f"{source}"
            )

            if search_text not in searchable:
                continue

            # Basic relevance:
            # title match gets higher priority,
            # then content/source match.

            if search_text in title:
                relevance = 2
            else:
                relevance = 1

            matches.append(
                (
                    relevance,
                    entry,
                )
            )

        matches.sort(
            key=lambda item: (
                item[0],
                item[1].get(
                    "created_at",
                    "",
                ),
            ),
            reverse=True,
        )

        return [
            entry
            for _, entry in matches[:limit]
        ]

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        investigation_id: int,
        memory_id: int,
        content: str | None = None,
        title: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Update an existing memory entry.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return None

        entry = self.get(
            investigation_id,
            memory_id,
        )

        if entry is None:
            return None

        if content is not None:

            if not content.strip():
                raise ValueError(
                    "Memory content cannot be empty."
                )

            entry["content"] = (
                content.strip()
            )

        if title is not None:

            entry["title"] = (
                title.strip()
                if title.strip()
                else None
            )

        if source is not None:
            entry["source"] = source

        if metadata is not None:
            entry["metadata"] = metadata

        entry["updated_at"] = self._now()

        memory = self._get_memory(
            investigation
        )

        self._replace_entry(
            memory,
            entry,
        )

        self._save_memory(
            investigation,
            memory,
        )

        return entry

    # ========================================================
    # DELETE
    # ========================================================

    def delete(
        self,
        investigation_id: int,
        memory_id: int,
    ) -> bool:
        """
        Delete one memory entry.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return False

        memory = self._get_memory(
            investigation
        )

        original_length = len(
            memory
        )

        memory = [
            entry
            for entry in memory
            if entry.get("id") != memory_id
        ]

        if len(memory) == original_length:
            return False

        self._save_memory(
            investigation,
            memory,
        )

        return True

    # ========================================================
    # ADD FINDING
    # ========================================================

    def add_finding(
        self,
        investigation_id: int,
        title: str,
        content: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method for adding an analytical finding.
        """

        return self.add(
            investigation_id=investigation_id,
            content=content,
            memory_type="finding",
            title=title,
            source=source,
            metadata=metadata,
        )

    # ========================================================
    # ADD OBSERVATION
    # ========================================================

    def add_observation(
        self,
        investigation_id: int,
        content: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method for investigator observations.
        """

        return self.add(
            investigation_id=investigation_id,
            content=content,
            memory_type="observation",
            source=source,
            metadata=metadata,
        )

    # ========================================================
    # ADD DECISION
    # ========================================================

    def add_decision(
        self,
        investigation_id: int,
        title: str,
        content: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Record an investigation decision/context entry.
        """

        return self.add(
            investigation_id=investigation_id,
            content=content,
            memory_type="decision",
            title=title,
            source=source,
            metadata=metadata,
        )

    # ========================================================
    # ADD ANALYSIS
    # ========================================================

    def add_analysis(
        self,
        investigation_id: int,
        title: str,
        content: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Store an analytical result in case memory.
        """

        return self.add(
            investigation_id=investigation_id,
            content=content,
            memory_type="analysis",
            title=title,
            source=source,
            metadata=metadata,
        )

    # ========================================================
    # CONTEXT
    # ========================================================

    def get_context(
        self,
        investigation_id: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most recent memory entries for use as
        investigation context.
        """

        return self.list(
            investigation_id=investigation_id,
            limit=limit,
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    def summary(
        self,
        investigation_id: int,
    ) -> dict[str, Any]:
        """
        Return a summary of the investigation memory.
        """

        investigation = self._get_investigation(
            investigation_id
        )

        if investigation is None:
            return {
                "investigation_id": investigation_id,
                "total": 0,
                "types": {},
            }

        memory = self._get_memory(
            investigation
        )

        type_counts = {
            memory_type: 0
            for memory_type
            in self.VALID_MEMORY_TYPES
        }

        for entry in memory:

            memory_type = entry.get(
                "type"
            )

            if memory_type in type_counts:
                type_counts[
                    memory_type
                ] += 1

        return {
            "investigation_id": investigation_id,
            "total": len(memory),
            "types": type_counts,
        }

    # ========================================================
    # INTERNAL: GET INVESTIGATION
    # ========================================================

    def _get_investigation(
        self,
        investigation_id: int,
    ) -> Investigation | None:
        """
        Retrieve an investigation.
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
    # INTERNAL: GET MEMORY
    # ========================================================

    @staticmethod
    def _get_memory(
        investigation: Investigation,
    ) -> list[dict[str, Any]]:
        """
        Retrieve memory entries from investigation metadata.
        """

        metadata = (
            investigation.metadata_json
            or {}
        )

        memory = metadata.get(
            "memory",
            [],
        )

        if not isinstance(
            memory,
            list,
        ):
            return []

        return memory

    # ========================================================
    # INTERNAL: SAVE MEMORY
    # ========================================================

    def _save_memory(
        self,
        investigation: Investigation,
        memory: list[dict[str, Any]],
    ) -> None:
        """
        Persist memory into investigation metadata.
        """

        current_metadata = (
            investigation.metadata_json
            or {}
        )

        investigation.metadata_json = {
            **current_metadata,
            "memory": memory,
        }

        if hasattr(
            investigation,
            "updated_at",
        ):
            investigation.updated_at = (
                datetime.now(
                    timezone.utc
                )
            )

        self.session.commit()

        self.session.refresh(
            investigation
        )

    # ========================================================
    # INTERNAL: REPLACE
    # ========================================================

    @staticmethod
    def _replace_entry(
        memory: list[dict[str, Any]],
        updated_entry: dict[str, Any],
    ) -> None:
        """
        Replace an existing memory entry in-place.
        """

        memory_id = updated_entry.get(
            "id"
        )

        for index, entry in enumerate(
            memory
        ):

            if entry.get("id") == memory_id:

                memory[index] = (
                    updated_entry
                )

                return

        raise ValueError(
            "Memory entry not found."
        )

    # ========================================================
    # INTERNAL: NEXT ID
    # ========================================================

    @staticmethod
    def _next_memory_id(
        memory: list[dict[str, Any]],
    ) -> int:
        """
        Generate the next memory ID.
        """

        if not memory:
            return 1

        ids = [
            int(entry.get("id", 0))
            for entry in memory
            if entry.get("id") is not None
        ]

        if not ids:
            return 1

        return max(ids) + 1

    # ========================================================
    # INTERNAL: VALIDATION
    # ========================================================

    @classmethod
    def _validate_memory_type(
        cls,
        memory_type: str,
    ) -> None:
        """
        Validate memory type.
        """

        if memory_type not in cls.VALID_MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory type "
                f"'{memory_type}'. Allowed values: "
                f"{', '.join(sorted(cls.VALID_MEMORY_TYPES))}."
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
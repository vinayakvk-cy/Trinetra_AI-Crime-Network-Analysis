"""
TRINETRA Criminal Documentary
=============================

Builds a chronological, evidence-grounded narrative from
structured investigation data.

Responsibilities
----------------
- Organize investigation events chronologically
- Convert case memory into narrative sections
- Include investigation actions and results
- Include analytical observations
- Clearly separate facts from analytical interpretation
- Produce a documentary-style structured output

This module does NOT:
- Invent events
- Determine guilt
- Create fictional evidence
- Replace investigator judgment
- Modify database or graph data
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.intelligence.investigation_context import InvestigationContext
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.investigations.action_manager import (
    InvestigationActionManager,
)
from app.investigations.case_memory import CaseMemory
from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.investigation_evidence import (
    InvestigationEvidence,
)
from app.models.investigation import Investigation


# ============================================================
# DOCUMENTARY EVENT
# ============================================================


@dataclass
class DocumentaryEvent:
    """
    One chronological event in the documentary.
    """

    event_id: str

    timestamp: str | None

    event_type: str

    title: str

    description: str

    source: str | None = None

    evidentiary_status: str = "documented"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to dictionary.
        """

        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "evidentiary_status": (
                self.evidentiary_status
            ),
            "metadata": self.metadata,
        }


# ============================================================
# DOCUMENTARY
# ============================================================


@dataclass
class CriminalDocumentary:
    """
    Complete documentary-style investigation report.
    """

    documentary_id: str

    investigation_id: int

    case_id: int | None

    title: str

    generated_at: str

    introduction: str

    timeline: list[DocumentaryEvent] = field(
        default_factory=list
    )

    findings: list[dict[str, Any]] = field(
        default_factory=list
    )

    analytical_observations: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    unresolved_questions: list[str] = field(
        default_factory=list
    )

    conclusion: str = ""

    disclaimer: str = (
        "This documentary is generated from available "
        "investigative information. Narrative presentation "
        "does not establish guilt, intent, or criminal "
        "responsibility."
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert documentary to API-friendly dictionary.
        """

        return {
            "documentary_id": self.documentary_id,
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "title": self.title,
            "generated_at": self.generated_at,
            "introduction": self.introduction,
            "timeline": [
                event.to_dict()
                for event in self.timeline
            ],
            "findings": self.findings,
            "analytical_observations": (
                self.analytical_observations
            ),
            "unresolved_questions": (
                self.unresolved_questions
            ),
            "conclusion": self.conclusion,
            "disclaimer": self.disclaimer,
        }


# ============================================================
# DOCUMENTARY GENERATOR
# ============================================================


class CriminalDocumentaryGenerator:
    """
    Generates an evidence-grounded documentary from an
    investigation.
    """

    def __init__(
        self,
        session,
    ) -> None:

        self.session = session

        self.action_manager = (
            InvestigationActionManager(
                session
            )
        )

        self.case_memory = CaseMemory(
            session
        )

    # ========================================================
    # GENERATE
    # ========================================================

    def generate(
        self,
        investigation_id: int,
        include_actions: bool = True,
        include_notes: bool = True,
    ) -> CriminalDocumentary:
        """
        Generate a documentary representation of an
        investigation.

        Existing memory/action behavior is preserved.

        Investigation-linked evidence is additionally included
        using the explicit InvestigationEvidence relationship.
        """

    # ========================================================
    # INVESTIGATION
    # ========================================================

        investigation = self.session.get(
            Investigation,
            investigation_id,
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        documentary_id = (
            self._build_documentary_id(
                investigation_id
            )
        )

        # ========================================================
        # EXISTING MEMORY BEHAVIOR
        # ========================================================

        memory = (
            self.case_memory.list(
                investigation_id=investigation_id,
                limit=500,
            )
        )

        # ========================================================
        # EXISTING ACTION BEHAVIOR
        # ========================================================

        actions: list[dict[str, Any]] = []

        if include_actions:
            actions = (
                self.action_manager.list_actions(
                    investigation_id
                )
            )

        # ========================================================
        # EXISTING MEMORY TIMELINE
        # ========================================================

        timeline = self._build_memory_timeline(
            memory
        )

        # ========================================================
        # EXISTING ACTION TIMELINE
        # ========================================================

        if include_actions:
            timeline.extend(
                self._build_action_timeline(
                    actions
                )
            )

        # ========================================================
        # INVESTIGATION-LINKED EVIDENCE
        # ========================================================

        investigation_links = (
            self.session.query(
                InvestigationEvidence
            )
            .filter(
                InvestigationEvidence.investigation_id
                == investigation_id
            )
            .order_by(
                InvestigationEvidence.id.asc()
            )
            .all()
        )

        evidence_ids = [
            link.evidence_id
            for link in investigation_links
            if link.evidence_id is not None
        ]

        evidence_records: list[Evidence] = []

        if evidence_ids:
            evidence_records = (
                self.session.query(Evidence)
                .filter(
                    Evidence.id.in_(evidence_ids)
                )
                .order_by(
                    Evidence.id.asc()
                )
                .all()
            )

        evidence_by_id = {
            evidence.id: evidence
            for evidence in evidence_records
        }

        # ========================================================
        # EVIDENCE TIMELINE
        # ========================================================

        timeline.extend(
            self._build_evidence_timeline(
                evidence_records,
                investigation_links,
            )
        )

        # ========================================================
        # EVIDENCE-BACKED RELATIONSHIPS
        # ========================================================

        relationships: list[
            EntityRelationship
        ] = []

        if evidence_ids:
            relationships = (
                self.session.query(
                    EntityRelationship
                )
                .filter(
                    EntityRelationship.evidence_id.in_(
                        evidence_ids
                    )
                )
                .order_by(
                    EntityRelationship.id.asc()
                )
                .all()
            )

        # ========================================================
        # ENTITIES FOR RELATIONSHIPS
        # ========================================================

        entity_ids: set[int] = set()

        for relationship in relationships:

            source_id = getattr(
                relationship,
                "source_entity_id",
                None,
            )

            target_id = getattr(
                relationship,
                "target_entity_id",
                None,
            )

            if source_id is not None:
                entity_ids.add(source_id)

            if target_id is not None:
                entity_ids.add(target_id)

        entities: list[Entity] = []

        if entity_ids:
            entities = (
                self.session.query(Entity)
                .filter(
                    Entity.id.in_(entity_ids)
                )
                .all()
            )

        entity_by_id = {
            entity.id: entity
            for entity in entities
        }

        # ========================================================
        # EXISTING FINDINGS
        # ========================================================

        findings = (
            self._extract_findings(
                memory
            )
        )

        # Add investigation-linked evidence
        # without removing existing findings.
        findings.extend(
            self._build_evidence_findings(
                evidence_records,
                investigation_links,
            )
        )

        # ========================================================
        # EXISTING ANALYTICAL OBSERVATIONS
        # ========================================================

        analytical_observations = (
            self._extract_analytical_observations(
                memory
            )
        )

        # Add explicit evidence-backed relationships.
        analytical_observations.extend(
            self._build_relationship_observations(
                relationships=relationships,
                entity_by_id=entity_by_id,
                evidence_by_id=evidence_by_id,
            )
        )

        # ========================================================
        # EXISTING UNRESOLVED QUESTIONS
        # ========================================================

        unresolved_questions = (
            self._build_unresolved_questions(
                memory=memory,
                actions=actions,
            )
        )

        # Add only evidence-processing questions.
        unresolved_questions.extend(
            self._build_evidence_questions(
                evidence_records
            )
        )

        # Remove duplicate questions while
        # preserving the existing order.
        unresolved_questions = list(
            dict.fromkeys(
                unresolved_questions
            )
        )

        # ========================================================
        # SORT TIMELINE
        # ========================================================

        timeline.sort(
            key=self._timeline_sort_key
        )

        # ========================================================
        # INTRODUCTION
        # ========================================================

        introduction = (
            self._build_introduction(
                investigation
            )
        )

        # ========================================================
        # CONCLUSION
        # ========================================================

        conclusion = (
            self._build_conclusion(
                investigation=investigation,
                timeline=timeline,
                findings=findings,
                analytical_observations=(
                    analytical_observations
                ),
                unresolved_questions=(
                    unresolved_questions
                ),
            )
        )

        # ========================================================
        # EXISTING NOTE FILTER
        # ========================================================

        if not include_notes:

            timeline = [
                event
                for event in timeline
                if event.event_type
                not in {
                    "note",
                    "observation",
                }
            ]

        # ========================================================
        # EXISTING RESPONSE STRUCTURE
        # ========================================================

        return CriminalDocumentary(
            documentary_id=documentary_id,
            investigation_id=investigation_id,
            case_id=getattr(
                investigation,
                "case_id",
                None,
            ),
            title=(
                f"Investigation Documentary — "
                f"{getattr(investigation, 'title', 'Investigation')}"
            ),
            generated_at=self._now(),
            introduction=introduction,
            timeline=timeline,
            findings=findings,
            analytical_observations=(
                analytical_observations
            ),
            unresolved_questions=(
                unresolved_questions
            ),
            conclusion=conclusion,
        )

    # ========================================================
    # MEMORY → TIMELINE
    # ========================================================

    @staticmethod
    def _build_memory_timeline(
        memory: list[dict[str, Any]],
    ) -> list[DocumentaryEvent]:
        """
        Convert case-memory entries into documentary events.
        """

        events: list[
            DocumentaryEvent
        ] = []

        for entry in memory:

            memory_id = entry.get(
                "id"
            )

            memory_type = entry.get(
                "type",
                "note",
            )

            title = (
                entry.get("title")
                or memory_type.replace(
                    "_",
                    " ",
                ).title()
            )

            content = str(
                entry.get(
                    "content",
                    "",
                )
            ).strip()

            if not content:
                continue

            evidentiary_status = (
                CriminalDocumentaryGenerator
                ._memory_evidentiary_status(
                    memory_type
                )
            )

            events.append(
                DocumentaryEvent(
                    event_id=(
                        f"memory-{memory_id}"
                    ),
                    timestamp=entry.get(
                        "created_at"
                    ),
                    event_type=memory_type,
                    title=title,
                    description=content,
                    source=entry.get(
                        "source"
                    ),
                    evidentiary_status=(
                        evidentiary_status
                    ),
                    metadata=(
                        entry.get(
                            "metadata"
                        )
                        or {}
                    ),
                )
            )

        return events

    # ========================================================
    # ACTION → TIMELINE
    # ========================================================

    @staticmethod
    def _build_action_timeline(
        actions: list[dict[str, Any]],
    ) -> list[DocumentaryEvent]:
        """
        Convert investigation actions into documentary events.
        """

        events: list[
            DocumentaryEvent
        ] = []

        for action in actions:

            action_id = action.get(
                "id"
            )

            title = (
                action.get("title")
                or "Investigation Action"
            )

            description = (
                action.get("description")
                or ""
            )

            status = action.get(
                "status",
                "pending",
            )

            result = action.get(
                "result"
            )

            if result is not None:

                description = (
                    f"{description} "
                    f"Result: {result}"
                ).strip()

            if not description:

                description = (
                    f"Investigation action "
                    f"status: {status}."
                )

            timestamp = (
                action.get("completed_at")
                or action.get("started_at")
                or action.get("created_at")
            )

            events.append(
                DocumentaryEvent(
                    event_id=(
                        f"action-{action_id}"
                    ),
                    timestamp=timestamp,
                    event_type="action",
                    title=title,
                    description=description,
                    source=(
                        action.get(
                            "assigned_to"
                        )
                    ),
                    evidentiary_status=(
                        "investigative_activity"
                    ),
                    metadata={
                        "action_id": action_id,
                        "status": status,
                        "priority": action.get(
                            "priority"
                        ),
                        "action_type": action.get(
                            "action_type"
                        ),
                    },
                )
            )

        return events

        # ========================================================
    # EVIDENCE → TIMELINE
    # ========================================================

    @staticmethod
    def _build_evidence_timeline(
        evidence_records: list[Evidence],
        investigation_links: list[
            InvestigationEvidence
        ],
    ) -> list[DocumentaryEvent]:
        """
        Convert investigation-linked evidence into
        documentary timeline events.

        This does not modify evidence records.
        """

        relation_by_evidence_id = {
            link.evidence_id: (
                CriminalDocumentaryGenerator
                ._enum_value(link.relation)
            )
            for link in investigation_links
            if link.evidence_id is not None
        }

        events: list[DocumentaryEvent] = []

        for evidence in evidence_records:

            evidence_number = (
                evidence.evidence_number
                or f"EVIDENCE-{evidence.id}"
            )

            evidence_type = (
                CriminalDocumentaryGenerator
                ._enum_value(
                    evidence.evidence_type
                )
            )

            evidence_status = (
                CriminalDocumentaryGenerator
                ._enum_value(
                    evidence.status
                )
            )

            relation = (
                relation_by_evidence_id.get(
                    evidence.id,
                    "relevant",
                )
            )

            description_parts = [
                (
                    f"Evidence {evidence_number} "
                    f"({evidence_type}) is explicitly "
                    f"linked to this investigation "
                    f"as '{relation}'."
                )
            ]

            if evidence.description:
                description_parts.append(
                    evidence.description.strip()
                )

            if evidence_status:
                description_parts.append(
                    f"Recorded evidence status: "
                    f"{evidence_status}."
                )

            if evidence.source_reference:
                description_parts.append(
                    f"Source reference: "
                    f"{evidence.source_reference}."
                )

            timestamp = None

            if evidence.created_at:
                timestamp = (
                    evidence.created_at.isoformat()
                )

            events.append(
                DocumentaryEvent(
                    event_id=(
                        f"evidence-{evidence.id}"
                    ),
                    timestamp=timestamp,
                    event_type="evidence",
                    title=(
                        evidence.title
                        or evidence_number
                    ),
                    description=" ".join(
                        description_parts
                    ),
                    source=(
                        evidence.source_reference
                    ),
                    evidentiary_status=(
                        "documented_evidence"
                    ),
                    metadata={
                        "evidence_id": evidence.id,
                        "evidence_number": (
                            evidence_number
                        ),
                        "evidence_type": (
                            evidence_type
                        ),
                        "status": (
                            evidence_status
                        ),
                        "investigation_relation": (
                            relation
                        ),
                    },
                )
            )

        return events

        # ========================================================
    # EVIDENCE → FINDINGS
    # ========================================================

    @staticmethod
    def _build_evidence_findings(
        evidence_records: list[Evidence],
        investigation_links: list[
            InvestigationEvidence
        ],
    ) -> list[dict[str, Any]]:
        """
        Convert investigation-linked evidence into
        documented findings.

        Existing memory findings are not replaced.
        """

        relation_by_evidence_id = {
            link.evidence_id: (
                CriminalDocumentaryGenerator
                ._enum_value(link.relation)
            )
            for link in investigation_links
            if link.evidence_id is not None
        }

        findings: list[
            dict[str, Any]
        ] = []

        for evidence in evidence_records:

            evidence_number = (
                evidence.evidence_number
                or f"EVIDENCE-{evidence.id}"
            )

            content = (
                evidence.description
                or evidence.extracted_text
                or (
                    "Evidence record is explicitly "
                    "linked to this investigation."
                )
            )

            findings.append(
                {
                    "id": (
                        f"evidence-{evidence.id}"
                    ),
                    "type": (
                        "documented_evidence"
                    ),
                    "title": (
                        evidence.title
                        or evidence_number
                    ),
                    "content": content,
                    "source": (
                        evidence.source_reference
                    ),
                    "created_at": (
                        evidence.created_at.isoformat()
                        if evidence.created_at
                        else None
                    ),
                    "metadata": {
                        "evidence_id": evidence.id,
                        "evidence_number": (
                            evidence_number
                        ),
                        "evidence_type": (
                            CriminalDocumentaryGenerator
                            ._enum_value(
                                evidence.evidence_type
                            )
                        ),
                        "status": (
                            CriminalDocumentaryGenerator
                            ._enum_value(
                                evidence.status
                            )
                        ),
                        "investigation_relation": (
                            relation_by_evidence_id.get(
                                evidence.id,
                                "relevant",
                            )
                        ),
                        "extraction_confidence": (
                            evidence.extraction_confidence
                        ),
                    },
                }
            )

        return findings

        # ========================================================
    # RELATIONSHIP → ANALYTICAL OBSERVATIONS
    # ========================================================

    @staticmethod
    def _build_relationship_observations(
        relationships: list[
            EntityRelationship
        ],
        entity_by_id: dict[
            int,
            Entity,
        ],
        evidence_by_id: dict[
            int,
            Evidence,
        ],
    ) -> list[dict[str, Any]]:
        """
        Convert explicitly evidence-backed relationships
        into analytical observations.

        The relationship evidence_id remains authoritative.
        """

        observations: list[
            dict[str, Any]
        ] = []

        for relationship in relationships:

            source_id = getattr(
                relationship,
                "source_entity_id",
                None,
            )

            target_id = getattr(
                relationship,
                "target_entity_id",
                None,
            )

            source = entity_by_id.get(
                source_id
            )

            target = entity_by_id.get(
                target_id
            )

            if source is None or target is None:
                continue

            source_name = (
                getattr(
                    source,
                    "name",
                    None,
                )
                or getattr(
                    source,
                    "value",
                    None,
                )
                or f"Entity {source.id}"
            )

            target_name = (
                getattr(
                    target,
                    "name",
                    None,
                )
                or getattr(
                    target,
                    "value",
                    None,
                )
                or f"Entity {target.id}"
            )

            relationship_type = (
                CriminalDocumentaryGenerator
                ._enum_value(
                    getattr(
                        relationship,
                        "relationship_type",
                        None,
                    )
                )
            )

            evidence_id = getattr(
                relationship,
                "evidence_id",
                None,
            )

            evidence = (
                evidence_by_id.get(
                    evidence_id
                )
                if evidence_id is not None
                else None
            )

            evidence_number = (
                evidence.evidence_number
                if evidence is not None
                else (
                    f"EVIDENCE-{evidence_id}"
                    if evidence_id is not None
                    else None
                )
            )

            content = (
                f"{source_name} is recorded as "
                f"{relationship_type} "
                f"{target_name}."
            )

            if evidence_number:
                content += (
                    f" The relationship is explicitly "
                    f"linked to {evidence_number}."
                )

            relationship_description = getattr(
                relationship,
                "description",
                None,
            )

            if relationship_description:
                content += (
                    " Recorded relationship description: "
                    f"{relationship_description.strip()}"
                )

            observations.append(
                {
                    "id": (
                        f"relationship-"
                        f"{relationship.id}"
                    ),
                    "type": (
                        "evidence_backed_relationship"
                    ),
                    "title": (
                        f"{source_name} "
                        f"{relationship_type} "
                        f"{target_name}"
                    ),
                    "content": content,
                    "source": (
                        getattr(
                            relationship,
                            "source_reference",
                            None,
                        )
                        or (
                            f"evidence:{evidence_id}"
                            if evidence_id is not None
                            else None
                        )
                    ),
                    "created_at": (
                        relationship.created_at.isoformat()
                        if getattr(
                            relationship,
                            "created_at",
                            None,
                        )
                        else None
                    ),
                    "metadata": {
                        "relationship_id": (
                            relationship.id
                        ),
                        "source_entity_id": (
                            source_id
                        ),
                        "target_entity_id": (
                            target_id
                        ),
                        "relationship_type": (
                            relationship_type
                        ),
                        "confidence": getattr(
                            relationship,
                            "confidence",
                            None,
                        ),
                        "evidence_id": (
                            evidence_id
                        ),
                        "evidence_number": (
                            evidence_number
                        ),
                    },
                    "interpretation_status": (
                        "analytical_observation"
                    ),
                }
            )

        return observations

        # ========================================================
    # EVIDENCE → UNRESOLVED QUESTIONS
    # ========================================================

    @staticmethod
    def _build_evidence_questions(
        evidence_records: list[Evidence],
    ) -> list[str]:
        """
        Surface questions only when the recorded evidence
        processing status indicates additional review.
        """

        questions: list[str] = []

        for evidence in evidence_records:

            evidence_number = (
                evidence.evidence_number
                or f"EVIDENCE-{evidence.id}"
            )

            evidence_status = (
                CriminalDocumentaryGenerator
                ._enum_value(
                    evidence.status
                )
            )

            if evidence_status == "pending_review":

                questions.append(
                    f"What review remains for "
                    f"evidence '{evidence_number}'?"
                )

            elif evidence_status == "under_analysis":

                questions.append(
                    f"What analysis remains for "
                    f"evidence '{evidence_number}'?"
                )

            elif evidence_status == "disputed":

                questions.append(
                    f"What issues are recorded as disputed "
                    f"for evidence '{evidence_number}'?"
                )

        return questions
    # ========================================================
    # FINDINGS
    # ========================================================

    @staticmethod
    def _extract_findings(
        memory: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract documented findings from case memory.
        """

        findings = []

        for entry in memory:

            if entry.get("type") != "finding":
                continue

            findings.append(
                {
                    "id": entry.get(
                        "id"
                    ),
                    "title": entry.get(
                        "title"
                    ),
                    "content": entry.get(
                        "content"
                    ),
                    "source": entry.get(
                        "source"
                    ),
                    "created_at": entry.get(
                        "created_at"
                    ),
                    "metadata": (
                        entry.get(
                            "metadata"
                        )
                        or {}
                    ),
                }
            )

        return findings

    # ========================================================
    # ANALYTICAL OBSERVATIONS
    # ========================================================

    @staticmethod
    def _extract_analytical_observations(
        memory: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract analytical observations.

        These are intentionally kept separate from findings
        because an analytical signal is not automatically a
        verified fact.
        """

        analytical_types = {
            "analysis",
            "relationship_review",
            "entity_review",
            "evidence_review",
        }

        observations = []

        for entry in memory:

            if entry.get("type") not in analytical_types:
                continue

            observations.append(
                {
                    "id": entry.get(
                        "id"
                    ),
                    "type": entry.get(
                        "type"
                    ),
                    "title": entry.get(
                        "title"
                    ),
                    "content": entry.get(
                        "content"
                    ),
                    "source": entry.get(
                        "source"
                    ),
                    "created_at": entry.get(
                        "created_at"
                    ),
                    "metadata": (
                        entry.get(
                            "metadata"
                        )
                        or {}
                    ),
                    "interpretation_status": (
                        "analytical_observation"
                    ),
                }
            )

        return observations

    # ========================================================
    # UNRESOLVED QUESTIONS
    # ========================================================

    @staticmethod
    def _build_unresolved_questions(
        memory: list[dict[str, Any]],
        actions: list[dict[str, Any]],
    ) -> list[str]:
        """
        Generate explicit unresolved investigation questions.

        This does not speculate about answers.
        """

        questions: list[str] = []

        # ----------------------------------------------------
        # Blocked actions
        # ----------------------------------------------------

        for action in actions:

            if action.get("status") != "blocked":
                continue

            title = action.get(
                "title",
                "Investigation action",
            )

            questions.append(
                f"Why does the investigation action "
                f"'{title}' remain blocked?"
            )

        # ----------------------------------------------------
        # Pending actions
        # ----------------------------------------------------

        for action in actions:

            if action.get("status") != "pending":
                continue

            title = action.get(
                "title",
                "Investigation action",
            )

            questions.append(
                f"What is required to complete "
                f"the pending action '{title}'?"
            )

        # ----------------------------------------------------
        # Explicit question-like memory
        # ----------------------------------------------------

        for entry in memory:

            content = str(
                entry.get(
                    "content",
                    "",
                )
            ).strip()

            if not content:
                continue

            if (
                content.endswith("?")
                and content not in questions
            ):
                questions.append(
                    content
                )

        return questions

        # ========================================================
    # INTRODUCTION
    # ========================================================

    @staticmethod
    def _build_introduction(
        investigation,
    ) -> str:
        """
        Build documentary introduction.

        Keeps the original narrative style while using
        fields that exist on the current Investigation model.
        """

        title = getattr(
            investigation,
            "title",
            "Investigation",
        )

        status = (
            CriminalDocumentaryGenerator
            ._enum_value(
                getattr(
                    investigation,
                    "status",
                    "unknown",
                )
            )
        )

        objective = getattr(
            investigation,
            "objective",
            None,
        )

        introduction = (
            f"This documentary presents the recorded "
            f"investigative history of '{title}'. "
            f"The investigation is currently marked "
            f"as {status}."
        )

        if objective:
            introduction += (
                " The recorded investigation objective is: "
                f"{objective.strip()}"
            )

        introduction += (
            " The timeline below is assembled from "
            "investigation-linked evidence, available "
            "case-memory entries, and investigation activities."
        )

        return introduction

       # ========================================================
    # CONCLUSION
    # ========================================================

    @staticmethod
    def _build_conclusion(
        investigation,
        timeline: list[DocumentaryEvent],
        findings: list[
            dict[str, Any]
        ],
        analytical_observations: list[
            dict[str, Any]
        ],
        unresolved_questions: list[str],
    ) -> str:
        """
        Build a cautious conclusion based only on recorded
        investigation information.
        """

        status = (
            CriminalDocumentaryGenerator
            ._enum_value(
                getattr(
                    investigation,
                    "status",
                    "unknown",
                )
            )
        )

        parts = []

        parts.append(
            f"The investigation is currently recorded "
            f"with status '{status}'."
        )

        if timeline:
            parts.append(
                f" The documentary contains "
                f"{len(timeline)} recorded "
                f"timeline event(s)."
            )

        if findings:
            parts.append(
                f" {len(findings)} documented "
                f"finding(s) are available."
            )

        if analytical_observations:
            parts.append(
                f" {len(analytical_observations)} "
                f"analytical observation(s) are recorded."
            )

        if unresolved_questions:
            parts.append(
                f" {len(unresolved_questions)} "
                f"unresolved question(s) remain recorded."
            )

        parts.append(
            " The available material should be reviewed "
            "against the underlying source evidence before "
            "drawing investigative or legal conclusions."
        )

        return "".join(parts)

    # ========================================================
    # EVIDENTIARY STATUS
    # ========================================================

    @staticmethod
    def _memory_evidentiary_status(
        memory_type: str,
    ) -> str:
        """
        Classify the role of a memory entry in the narrative.
        """

        mapping = {
            "finding": "documented_finding",
            "evidence_review": "evidence_review",
            "entity_review": "analytical_review",
            "relationship_review": "analytical_review",
            "analysis": "analytical_observation",
            "observation": "investigator_observation",
            "decision": "investigative_decision",
            "note": "investigator_note",
            "system": "system_record",
        }

        return mapping.get(
            memory_type,
            "documented",
        )

        # ========================================================
    # ENUM NORMALIZATION
    # ========================================================

    @staticmethod
    def _enum_value(
        value: Any,
    ) -> str:
        """
        Normalize enum values for documentary output.
        """

        if value is None:
            return ""

        return str(
            getattr(
                value,
                "value",
                value,
            )
        )

    # ========================================================
    # SORT
    # ========================================================

    @staticmethod
    def _timeline_sort_key(
        event: DocumentaryEvent,
    ) -> tuple[int, str]:
        """
        Sort events chronologically.

        Events without timestamps are placed after
        timestamped events.
        """

        timestamp = event.timestamp

        if not timestamp:
            return (
                1,
                "",
            )

        return (
            0,
            timestamp,
        )

    # ========================================================
    # DOCUMENTARY ID
    # ========================================================

    @staticmethod
    def _build_documentary_id(
        investigation_id: int,
    ) -> str:
        """
        Generate documentary identifier.
        """

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d%H%M%S"
        )

        return (
            f"CD-{investigation_id}-"
            f"{timestamp}"
        )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    @staticmethod
    def _now() -> str:
        """
        Return current UTC timestamp.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_criminal_documentary(
    session,
    investigation_id: int,
) -> CriminalDocumentary:
    """
    Convenience wrapper for documentary generation.
    """

    generator = (
        CriminalDocumentaryGenerator(
            session
        )
    )

    return generator.generate(
        investigation_id=investigation_id
    )
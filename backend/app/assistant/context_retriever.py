"""
TRINETRA Context Retriever
==========================

Retrieves investigation context for the local assistant.

Responsibilities
----------------
- Retrieve investigation information
- Retrieve case-memory entries
- Retrieve investigation actions
- Retrieve relevant graph information
- Search case memory using keywords
- Assemble a unified assistant context

This module does NOT:
- Generate final answers
- Invent evidence
- Modify investigations
- Modify the graph
- Determine guilt
"""

from __future__ import annotations

from dataclasses import dataclass, field
from multiprocessing import context
from typing import Any

from app.graph.neo4j_client import Neo4jClient
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from app.models.investigation_evidence import InvestigationEvidence
from app.investigations.action_manager import (
    InvestigationActionManager,
)
from app.investigations.case_memory import CaseMemory
from app.investigations.investigation_store import (
    InvestigationStore,
)


# ============================================================
# CONTEXT RESULT
# ============================================================


@dataclass
class AssistantContext:
    """
    Complete context supplied to the local assistant.
    """

    investigation: dict[str, Any] | None = None

    entity: dict[str, Any] | None = None

    memory: list[dict[str, Any]] = field(
        default_factory=list
    )

    actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    graph: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = field(
        default_factory=list
    )

    relationship_evidence: list[dict[str, Any]] = field(
        default_factory=list
    )

    search_results: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert context into a dictionary.
        """

        return {
            "investigation": self.investigation,
            "entity": self.entity,
            "memory": self.memory,
            "actions": self.actions,
            "graph": self.graph,
            "evidence": self.evidence,
            "relationship_evidence": self.relationship_evidence,
            "search_results": self.search_results,
            "metadata": self.metadata,
        }


# ============================================================
# CONTEXT RETRIEVER
# ============================================================


class ContextRetriever:
    """
    Retrieves relevant investigation context for the assistant.
    """

    def __init__(
        self,
        session,
        neo4j_client: Neo4jClient | None = None,
    ) -> None:

        self.session = session

        self.investigation_store = (
            InvestigationStore(
                session
            )
        )

        self.case_memory = CaseMemory(
            session
        )

        self.action_manager = (
            InvestigationActionManager(
                session
            )
        )

        self.neo4j_client = neo4j_client

    # ========================================================
    # RETRIEVE FULL CONTEXT
    # ========================================================

    def retrieve(
        self,
        investigation_id: int,
        query: str | None = None,
        memory_limit: int = 20,
        action_limit: int = 50,
        graph_limit: int = 50,
    ) -> AssistantContext:
        """
        Retrieve a complete assistant context.

        If query is provided, case memory is searched for
        query-specific information.
        """

        investigation = (
            self.investigation_store.get_by_id(
                investigation_id
            )
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        investigation_data = (
            self._serialize_investigation(
                investigation
            )
        )

        memory = (
            self.case_memory.get_context(
                investigation_id,
                limit=memory_limit,
            )
        )

        actions = (
            self.action_manager.list_actions(
                investigation_id
            )
        )[:action_limit]

        search_results: list[
            dict[str, Any]
        ] = []

        if query and query.strip():

            search_results = (
                self.case_memory.search(
                    investigation_id=(
                        investigation_id
                    ),
                    query=query,
                    limit=memory_limit,
                )
            )

        graph = self._retrieve_graph_context(
            investigation=investigation,
            limit=graph_limit,
        )

        evidence = self._retrieve_evidence(
            investigation_id=investigation_id,
            limit=memory_limit,
        )

        metadata = {
            "investigation_id": investigation_id,
            "query": query,
            "memory_count": len(memory),
            "action_count": len(actions),
            "graph_count": len(graph),
            "evidence_count": len(evidence),
            "search_result_count": len(
                search_results
            ),
        }

        return AssistantContext(
            investigation=investigation_data,
            memory=memory,
            actions=actions,
            graph=graph,
            evidence=evidence,
            search_results=search_results,
            metadata=metadata,
        )

    # ========================================================
    # RETRIEVE EVIDENCE
    # ========================================================

    def _retrieve_evidence(
        self,
        investigation_id: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence linked to the investigation."""

        statement = (
            self.session.query(Evidence)
            .join(
                InvestigationEvidence,
                InvestigationEvidence.evidence_id == Evidence.id,
            )
            .filter(
                InvestigationEvidence.investigation_id == investigation_id
            )
            .order_by(Evidence.id.asc())
            .limit(limit)
        )

        records: list[dict[str, Any]] = []

        for evidence in statement.all():
            records.append(
                {
                    "id": evidence.id,
                    "case_id": evidence.case_id,
                    "evidence_number": evidence.evidence_number,
                    "title": evidence.title,
                    "description": evidence.description,
                    "evidence_type": getattr(evidence.evidence_type, "value", evidence.evidence_type),
                    "status": getattr(evidence.status, "value", evidence.status),
                    "source_type": evidence.source_type,
                    "source_reference": evidence.source_reference,
                    "source_file": evidence.source_file,
                    "extracted_text": evidence.extracted_text,
                    "extraction_confidence": evidence.extraction_confidence,
                    "forensic_result": evidence.forensic_result,
                    "forensic_confidence": evidence.forensic_confidence,
                }
            )

        return records

        # ========================================================
    # RETRIEVE RELATIONSHIP EVIDENCE
    # ========================================================

    def _retrieve_relationship_evidence(
        self,
        entity_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relationships for an entity together with
        the evidence explicitly linked to each relationship.

        The relationship's evidence_id is authoritative.
        This method does not infer evidence from text.
        """

        relationships = (
            self.session.query(EntityRelationship)
            .filter(
                (
                    (EntityRelationship.source_entity_id == entity_id)
                    | (EntityRelationship.target_entity_id == entity_id)
                )
            )
            .order_by(EntityRelationship.id.asc())
            .limit(limit)
            .all()
        )

        records: list[dict[str, Any]] = []

        for relationship in relationships:
            source = self.session.get(
                Entity,
                relationship.source_entity_id,
            )

            target = self.session.get(
                Entity,
                relationship.target_entity_id,
            )

            evidence = None

            if relationship.evidence_id is not None:
                evidence = self.session.get(
                    Evidence,
                    relationship.evidence_id,
                )

            relationship_type = getattr(
                relationship.relationship_type,
                "value",
                relationship.relationship_type,
            )

            record = {
                "relationship_id": relationship.id,
                "source_entity_id": relationship.source_entity_id,
                "source_entity_type": (
                    getattr(
                        source.entity_type,
                        "value",
                        source.entity_type,
                    )
                    if source
                    else None
                ),
                "source_entity_name": (
                    source.name
                    if source
                    else None
                ),
                "target_entity_id": relationship.target_entity_id,
                "target_entity_type": (
                    getattr(
                        target.entity_type,
                        "value",
                        target.entity_type,
                    )
                    if target
                    else None
                ),
                "target_entity_name": (
                    target.name
                    if target
                    else None
                ),
                "relationship_type": relationship_type,
                "description": relationship.description,
                "confidence": relationship.confidence,
                "evidence_id": relationship.evidence_id,
                "evidence_number": (
                    evidence.evidence_number
                    if evidence
                    else None
                ),
                "evidence_title": (
                    evidence.title
                    if evidence
                    else None
                ),
                "evidence_text": (
                    evidence.extracted_text
                    if evidence
                    else None
                ),
                "evidence_confidence": (
                    evidence.extraction_confidence
                    if evidence
                    else None
                ),
                "evidence_source_reference": (
                    evidence.source_reference
                    if evidence
                    else None
                ),
            }

            records.append(record)

        return records

    # ========================================================
    # RETRIEVE MEMORY
    # ========================================================

    def retrieve_memory(
        self,
        investigation_id: int,
        limit: int = 20,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve investigation memory.
        """

        return self.case_memory.list(
            investigation_id=investigation_id,
            memory_type=memory_type,
            limit=limit,
        )

    # ========================================================
    # SEARCH MEMORY
    # ========================================================

    def search_memory(
        self,
        investigation_id: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search investigation memory.
        """

        return self.case_memory.search(
            investigation_id=investigation_id,
            query=query,
            limit=limit,
        )

    # ========================================================
    # RETRIEVE ACTIONS
    # ========================================================

    def retrieve_actions(
        self,
        investigation_id: int,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve investigation actions.
        """

        actions = (
            self.action_manager.list_actions(
                investigation_id=investigation_id,
                status=status,
            )
        )

        return actions[:limit]

    # ========================================================
    # RETRIEVE GRAPH CONTEXT
    # ========================================================

    def retrieve_graph(
        self,
        entity_type: str,
        entity_value: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve graph relationships around an entity.
        """

        if self.neo4j_client is None:
            return []

        if not entity_type or not entity_value:
            return []

        query = """
        MATCH (n:Entity)
        WHERE n.entity_type = $entity_type
          AND (
              n.normalized_value = $normalized_value
              OR toLower(n.value) = $normalized_value
          )

        OPTIONAL MATCH (n)-[r]-(neighbor)

        RETURN
            n.entity_type AS entity_type,
            n.value AS value,
            type(r) AS relationship_type,
            neighbor.entity_type AS neighbor_type,
            neighbor.value AS neighbor_value
        LIMIT $limit
        """

        try:

            records = (
                self.neo4j_client.execute_read(
                    query,
                    {
                        "entity_type": entity_type,
                        "normalized_value": (
                            str(
                                entity_value
                            )
                            .strip()
                            .lower()
                        ),
                        "limit": limit,
                    },
                )
            )

            return [
                dict(record)
                for record in records
            ]

        except Exception:
            return []

    # ========================================================
    # ENTITY CONTEXT
    # ========================================================
    def _retrieve_entity(
        self,
        entity_type: str,
        entity_value: str,
    ) -> dict[str, Any] | None:
        """Retrieve the SQL entity record matching the focused graph entity."""

        normalized_value = str(entity_value).strip().lower()
        normalized_type = str(entity_type).strip().lower()

        if not normalized_value:
            return None

        candidates = (
            self.session.query(Entity)
            .filter(Entity.normalized_name == normalized_value)
            .all()
        )

        for entity in candidates:
            current_type = getattr(
                entity.entity_type,
                "value",
                entity.entity_type,
            )

            if str(current_type).strip().lower() != normalized_type:
                continue

            return {
                "id": entity.id,
                "entity_type": current_type,
                "name": entity.name,
                "normalized_name": entity.normalized_name,
                "external_id": getattr(entity, "external_id", None),
                "source": getattr(
                    entity.source,
                    "value",
                    entity.source,
                ),
                "source_reference": getattr(
                    entity,
                    "source_reference",
                    None,
                ),
                "description": getattr(
                    entity,
                    "description",
                    None,
                ),
                "extraction_method": getattr(
                    entity,
                    "extraction_method",
                    None,
                ),
                "extraction_confidence": getattr(
                    entity,
                    "extraction_confidence",
                    None,
                ),
                "linking_confidence": getattr(
                    entity,
                    "linking_confidence",
                    None,
                ),
                "graph_node_id": getattr(
                    entity,
                    "graph_node_id",
                    None,
                ),
                "risk_score": getattr(
                    entity,
                    "risk_score",
                    None,
                ),
            }

        return None


    def retrieve_entity_context(
        self,
        investigation_id: int,
        entity_type: str,
        entity_value: str,
        limit: int = 50,
    ) -> AssistantContext:
        """
        Retrieve investigation context focused on one entity.
        """

        context = self.retrieve(
            investigation_id=investigation_id,
            memory_limit=20,
            action_limit=50,
            graph_limit=limit,
        )

        context.graph = (
            self.retrieve_graph(
                entity_type=entity_type,
                entity_value=entity_value,
                limit=limit,
            )
        )

        context.entity = self._retrieve_entity(
            entity_type=entity_type,
            entity_value=entity_value,
        )



        if context.entity:
            context.relationship_evidence = (
                self._retrieve_relationship_evidence(
                    entity_id=context.entity["id"],
                    limit=limit,
                )
            )

            context.metadata[
                "relationship_evidence_count"
            ] = len(
                context.relationship_evidence
            )

        context.metadata[
            "focused_entity"
        ] = {
            "entity_type": entity_type,
            "entity_value": entity_value,
        }

        return context

    # ========================================================
    # QUERY CONTEXT
    # ========================================================

    def retrieve_query_context(
        self,
        investigation_id: int,
        query: str,
        memory_limit: int = 20,
        graph_limit: int = 50,
    ) -> AssistantContext:
        """
        Retrieve context specifically relevant to a user
        question.

        The method first retrieves the investigation's case
        graph, then focuses graph retrieval on an entity whose
        value appears in the user's question.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        context = self.retrieve(
            investigation_id=investigation_id,
            query=query,
            memory_limit=memory_limit,
            graph_limit=graph_limit,
        )

        normalized_query = query.strip().lower()

        # ----------------------------------------------------
        # Try to identify an entity mentioned in the question.
        # ----------------------------------------------------

        focused_entity = None
        focused_entity_type = None

        candidates: list[tuple[str, str]] = []

        for record in context.graph:
            value = record.get("neighbor_value")
            entity_type = record.get("neighbor_type")

            if value and entity_type:
                candidates.append(
                    (
                        str(entity_type),
                        str(value),
                    )
                )

        # Prefer longer entity names so multi-word names
        # are matched before shorter names.
        candidates = sorted(
            set(candidates),
            key=lambda item: len(item[1]),
            reverse=True,
        )

        for entity_type, candidate in candidates:
            if candidate.lower() in normalized_query:
                focused_entity = candidate
                focused_entity_type = entity_type
                break

        # ----------------------------------------------------
        # Retrieve the selected entity's own relationships.
        # ----------------------------------------------------

        if focused_entity and focused_entity_type:
            context.entity = self._retrieve_entity(
                entity_type=focused_entity_type,
                entity_value=focused_entity,
            )

            focused_graph = self.retrieve_graph(
                entity_type=focused_entity_type,
                entity_value=focused_entity,
                limit=graph_limit,
            )

            if focused_graph:
                context.graph = focused_graph

                context.metadata[
                    "focused_entity"
                ] = {
                    "entity_type": focused_entity_type,
                    "entity_value": focused_entity,
                }

            if context.entity:
                context.relationship_evidence = (
                    self._retrieve_relationship_evidence(
                        entity_id=context.entity["id"],
                        limit=graph_limit,
                    )
                )

                context.metadata[
                    "relationship_evidence_count"
                ] = len(
                    context.relationship_evidence
                )

        # ----------------------------------------------------
        # Refresh metadata after focused graph replacement.
        # ----------------------------------------------------

        context.metadata["memory_count"] = len(
            context.memory
        )

        context.metadata["action_count"] = len(
            context.actions
        )

        context.metadata["graph_count"] = len(
            context.graph
        )

        context.metadata["search_result_count"] = len(
            context.search_results
        )

        context.metadata[
            "relationship_evidence_count"
        ] = len(
            context.relationship_evidence
        )

        context.metadata[
            "retrieval_mode"
        ] = "keyword"

        return context
    # ========================================================
    # RELEVANT CONTEXT
    # ========================================================

    def build_relevant_context(
        self,
        investigation_id: int,
        query: str,
    ) -> dict[str, Any]:
        """
        Build a compact context package for the assistant.

        This is intended to be passed into the reasoning/
        response layer.
        """

        context = (
            self.retrieve_query_context(
                investigation_id=(
                    investigation_id
                ),
                query=query,
            )
        )

        return {
            "investigation": (
                context.investigation
            ),
            "relevant_memory": (
                context.search_results
            ),
            "recent_memory": (
                context.memory
            ),
            "actions": context.actions,
            "graph": context.graph,
            "metadata": context.metadata,
        }

    # ========================================================
    # INVESTIGATION SERIALIZATION
    # ========================================================

    def _serialize_investigation(
    self,
    investigation,
) -> dict[str, Any]:

        case_id = getattr(investigation, "case_id", None)

        case = None
        if case_id:
            case = self.session.get(Case, case_id)

        case_number = (
            getattr(case, "case_number", None)
            if case
            else None
        )

        return {
            "id": getattr(
                investigation,
                "id",
                None,
            ),
            "case_id": getattr(
                investigation,
                "case_id",
                None,
            ),

            "case_number": case_number,
            "case_value": case_number,

            "title": getattr(
                investigation,
                "title",
                None,
            ),
            "description": getattr(
                investigation,
                "description",
                None,
            ),
            "status": getattr(
                investigation,
                "status",
                None,
            ),
            "created_at": str(
                getattr(
                    investigation,
                    "created_at",
                    None,
                )
            ),
            "updated_at": str(
                getattr(
                    investigation,
                    "updated_at",
                    None,
                )
            ),
        }

    # ========================================================
    # GRAPH CONTEXT FROM INVESTIGATION
    # ========================================================

    def _retrieve_graph_context(
        self,
        investigation,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Retrieve graph information for the investigation's case.
        """

        if self.neo4j_client is None:
            return []

        case_id = getattr(
            investigation,
            "case_id",
            None,
        )

        if not case_id:
            return []

        try:
            case = self.session.get(
        Case,
        case_id,
    )
        except Exception:
            case = None

        if case is None:
            return []

        case_number = getattr(
            case,
            "case_number",
            None,
        )

        if not case_number:
            return []

        return self.retrieve_graph(
            entity_type="CASE",
            entity_value=case_number,
            limit=limit,
        )
    # ========================================================
    # CONTEXT SUMMARY
    # ========================================================

    def summarize(
        self,
        investigation_id: int,
    ) -> dict[str, Any]:
        """
        Return a compact summary of available assistant
        context.
        """

        investigation = (
            self.investigation_store.get_by_id(
                investigation_id
            )
        )

        if investigation is None:
            raise ValueError(
                "Investigation not found."
            )

        memory_summary = (
            self.case_memory.summary(
                investigation_id
            )
        )

        action_summary = (
            self.action_manager.summary(
                investigation_id
            )
        )

        return {
            "investigation": (
                self._serialize_investigation(
                    investigation
                )
            ),
            "memory": memory_summary,
            "actions": action_summary,
            "graph_available": (
                self.neo4j_client is not None
            ),
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def retrieve_assistant_context(
    session,
    investigation_id: int,
    query: str | None = None,
    neo4j_client: Neo4jClient | None = None,
) -> AssistantContext:
    """
    Convenience wrapper for context retrieval.
    """

    retriever = ContextRetriever(
        session=session,
        neo4j_client=neo4j_client,
    )

    return retriever.retrieve(
        investigation_id=investigation_id,
        query=query,
    )
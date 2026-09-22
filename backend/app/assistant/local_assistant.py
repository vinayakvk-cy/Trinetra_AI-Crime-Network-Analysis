from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.assistant.context_retriever import (
    AssistantContext,
    ContextRetriever,
)

from app.analytics.pattern_detector import PatternDetector
from app.analytics.risk_engine import RiskEngine


# ============================================================
# ASSISTANT RESPONSE
# ============================================================


@dataclass
class AssistantResponse:
    """
    Structured response returned by the local assistant.
    """

    investigation_id: int
    question: str
    answer: str
    intent: str
    confidence: str = "moderate"

    supporting_context: list[dict[str, Any]] = field(
        default_factory=list
    )

    uncertainties: list[str] = field(
        default_factory=list
    )

    suggested_next_steps: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    disclaimer: str = (
        "This response is generated from available "
        "investigative data. Analytical observations "
        "should be verified against underlying evidence."
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert response into an API-friendly dictionary.
        """

        return asdict(self)


# ============================================================
# LOCAL ASSISTANT
# ============================================================


class LocalInvestigationAssistant:
    """
    Evidence-grounded local investigation assistant.

    The implementation is deterministic and local.
    A local LLM can be connected later without changing
    the context-retrieval interface.
    """

    def __init__(
        self,
        session,
        neo4j_client=None,
    ) -> None:

        self.retriever = ContextRetriever(
            session=session,
            neo4j_client=neo4j_client,
        )

        self.risk_engine = (
            RiskEngine(neo4j_client)
            if neo4j_client is not None
            else None
        )

        self.pattern_detector = (
            PatternDetector(neo4j_client)
            if neo4j_client is not None
            else None
        )

    # ========================================================
    # ASK
    # ========================================================

    def ask(
        self,
        investigation_id: int,
        question: str,
    ) -> AssistantResponse:
        """
        Answer an investigator question using available
        investigation context.
        """

        question = self._validate_question(question)

        context = self.retriever.retrieve_query_context(
            investigation_id=investigation_id,
            query=question,
        )

        intent = self._classify_intent(question)

        return self._build_response(
            investigation_id=investigation_id,
            question=question,
            intent=intent,
            context=context,
        )

    # ========================================================
    # CONTEXT ONLY
    # ========================================================

    def get_context(
        self,
        investigation_id: int,
        question: str | None = None,
    ) -> dict[str, Any]:
        """
        Return assistant context without generating an answer.
        """

        context = self.retriever.retrieve(
            investigation_id=investigation_id,
            query=question,
        )

        return context.to_dict()

    # ========================================================
    # BUILD RESPONSE
    # ========================================================

    def _build_response(
        self,
        investigation_id: int,
        question: str,
        intent: str,
        context: AssistantContext,
    ) -> AssistantResponse:
        """
        Build a deterministic response from retrieved context.
        """

        supporting_context = self._build_supporting_context(
            context
        )

        uncertainties = self._identify_uncertainties(
            context
        )

        suggested_next_steps = self._suggest_next_steps(
            intent=intent,
            context=context,
        )

        answer = self._generate_answer(
            question=question,
            intent=intent,
            context=context,
        )

        confidence = self._calculate_confidence(
            context
        )

        return AssistantResponse(
            investigation_id=investigation_id,
            question=question,
            answer=answer,
            intent=intent,
            confidence=confidence,
            supporting_context=supporting_context,
            uncertainties=uncertainties,
            suggested_next_steps=suggested_next_steps,
            metadata={
                "retrieval_mode": context.metadata.get(
                    "retrieval_mode",
                    "standard",
                ),
                "memory_count": len(context.memory),
                "search_result_count": len(
                    context.search_results
                ),
                "graph_count": len(context.graph),
                "evidence_count": len(context.evidence),
                "relationship_evidence_count": len(
                    context.relationship_evidence
                ),
                "focused_entity": context.metadata.get(
                    "focused_entity"
                ),
                "entity_risk_score": (
                    context.entity.get("risk_score")
                    if context.entity
                    else None
                ),
            },
        )

    # ========================================================
    # INTENT CLASSIFICATION
    # ========================================================

    @staticmethod
    def _classify_intent(
        question: str,
    ) -> str:
        """
        Classify common investigator question types.
        """

        normalized = question.lower()

        if any(
            word in normalized
            for word in (
                "summarize",
                "summary",
                "overview",
                "what do we know",
            )
        ):
            return "summary"

        if any(
            word in normalized
            for word in (
                "evidence",
                "proof",
                "document",
                "record",
            )
        ):
            return "evidence"

        if any(
            word in normalized
            for word in (
                "connected",
                "connection",
                "relationship",
                "linked",
                "associated",
            )
        ):
            return "relationship"

        if any(
            word in normalized
            for word in (
                "pattern",
                "similar",
                "common",
                "cluster",
            )
        ):
            return "pattern"

        if any(
            word in normalized
            for word in (
                "risk",
                "priority",
                "threat",
            )
        ):
            return "risk"

        if any(
            word in normalized
            for word in (
                "next",
                "should we",
                "what should",
                "action",
                "investigate",
            )
        ):
            return "next_step"

        if any(
            word in normalized
            for word in (
                "timeline",
                "when",
                "date",
                "sequence",
            )
        ):
            return "timeline"

        return "general"

    # ========================================================
    # ANSWER GENERATION
    # ========================================================

    def _generate_answer(
        self,
        question: str,
        intent: str,
        context: AssistantContext,
    ) -> str:
        """
        Generate a deterministic evidence-grounded answer.
        """

        if intent == "summary":
            return self._evidence_aware_summary(context)

        if intent == "evidence":
            return self._evidence_answer(context)

        if intent == "relationship":
            return self._relationship_answer(context)

        if intent == "pattern":
            return self._pattern_answer(context)

        if intent == "risk":
            return self._risk_answer(context)

        if intent == "next_step":
            return self._next_step_answer(context)

        if intent == "timeline":
            return self._timeline_answer(context)

        return self._general_answer(
            question=question,
            context=context,
        )

    # ========================================================
    # EVIDENCE-AWARE SUMMARY
    # ========================================================

    def _evidence_aware_summary(
        self,
        context: AssistantContext,
    ) -> str:
        """
        Build an evidence-aware investigation summary.

        Relationship evidence is authoritative: a relationship is
        directly supported only when EntityRelationship.evidence_id
        explicitly links it to an Evidence record.
        """

        investigation = context.investigation or {}

        title = investigation.get(
            "title",
            "This investigation",
        )

        status = investigation.get(
            "status",
            "unknown",
        )

        status = getattr(
            status,
            "value",
            status,
        )

        parts: list[str] = [
            f"{title} is currently recorded with status '{status}'."
        ]

        # ----------------------------------------------------
        # Focused entity
        # ----------------------------------------------------

        entity = context.entity

        if entity:
            entity_name = entity.get(
                "name",
                "the focused entity",
            )

            parts.append(
                f"{entity_name} is the focused entity "
                "in the retrieved investigation context."
            )

        # ----------------------------------------------------
        # Authoritative relationship evidence
        # ----------------------------------------------------

        relationship_evidence = (
            context.relationship_evidence or []
        )

        directly_supported: list[dict[str, Any]] = []
        unsupported_relationships: list[dict[str, Any]] = []

        for relationship in relationship_evidence:

            if relationship.get("evidence_id") is not None:
                directly_supported.append(
                    relationship
                )
            else:
                unsupported_relationships.append(
                    relationship
                )

        if directly_supported:

            parts.append(
                "Directly supported relationships:"
            )

            for relationship in directly_supported:

                source_name = (
                    relationship.get(
                        "source_entity_name"
                    )
                    or "Unknown source"
                )

                target_name = (
                    relationship.get(
                        "target_entity_name"
                    )
                    or "Unknown target"
                )

                relationship_type = (
                    relationship.get(
                        "relationship_type"
                    )
                    or "related_to"
                )

                evidence_number = (
                    relationship.get(
                        "evidence_number"
                    )
                    or "Unknown evidence"
                )

                evidence_title = (
                    relationship.get(
                        "evidence_title"
                    )
                    or "Evidence record"
                )

                confidence = relationship.get(
                    "confidence"
                )

                relationship_text = (
                    f"{source_name} "
                    f"--{relationship_type.upper()}--> "
                    f"{target_name}"
                )

                evidence_text = (
                    f"{evidence_number} "
                    f"({evidence_title})"
                )

                if confidence is not None:
                    evidence_text += (
                        f", relationship confidence "
                        f"{float(confidence):.2f}"
                    )

                parts.append(
                    f"- {relationship_text}; "
                    f"explicitly linked to {evidence_text}."
                )

        if unsupported_relationships:

            parts.append(
                "Recorded relationships without "
                "explicitly linked evidence:"
            )

            for relationship in unsupported_relationships:

                source_name = (
                    relationship.get(
                        "source_entity_name"
                    )
                    or "Unknown source"
                )

                target_name = (
                    relationship.get(
                        "target_entity_name"
                    )
                    or "Unknown target"
                )

                relationship_type = (
                    relationship.get(
                        "relationship_type"
                    )
                    or "related_to"
                )

                relationship_text = (
                    f"{source_name} "
                    f"--{relationship_type.upper()}--> "
                    f"{target_name}"
                )

                confidence = relationship.get(
                    "confidence"
                )

                if confidence is not None:

                    parts.append(
                        f"- {relationship_text} "
                        f"(confidence "
                        f"{float(confidence):.2f}); "
                        "no evidence is explicitly linked "
                        "to this relationship."
                    )

                else:

                    parts.append(
                        f"- {relationship_text}; "
                        "no evidence is explicitly linked "
                        "to this relationship."
                    )

        # ----------------------------------------------------
        # Evidence records not explicitly linked to the
        # focused entity's relationships
        # ----------------------------------------------------

        explicitly_linked_evidence_ids = {
            relationship.get("evidence_id")
            for relationship in relationship_evidence
            if relationship.get("evidence_id") is not None
        }

        unrelated_evidence: list[dict[str, Any]] = []

        for evidence in context.evidence or []:

            evidence_id = evidence.get("id")

            if evidence_id not in (
                explicitly_linked_evidence_ids
            ):
                unrelated_evidence.append(
                    evidence
                )

        if unrelated_evidence:

            parts.append(
                "Other evidence retrieved for the "
                "investigation but not explicitly linked "
                "to the focused entity's relationships:"
            )

            for evidence in unrelated_evidence:

                evidence_number = evidence.get(
                    "evidence_number",
                    "Unknown evidence",
                )

                evidence_title = evidence.get(
                    "title",
                    "Evidence record",
                )

                evidence_text = (
                    evidence.get(
                        "extracted_text"
                    )
                    or evidence.get(
                        "description"
                    )
                    or ""
                ).strip()

                if evidence_text:
                    evidence_text = (
                        evidence_text.rstrip(".")
                        + "."
                    )

                if evidence_text:

                    parts.append(
                        f"- {evidence_number} "
                        f"({evidence_title}): "
                        f"{evidence_text}"
                    )

                else:

                    parts.append(
                        f"- {evidence_number} "
                        f"({evidence_title})."
                    )

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        if entity:

            risk_score = entity.get(
                "risk_score"
            )

            if risk_score is not None:

                parts.append(
                    f"Recorded entity risk score: "
                    f"{risk_score}/100."
                )

        # ----------------------------------------------------
        # Verification disclaimer
        # ----------------------------------------------------

        parts.append(
            "These are recorded intelligence signals "
            "and should be verified against the underlying "
            "source evidence."
        )

        return " ".join(parts)

    # ========================================================
    # SUMMARY
    # ========================================================

    @staticmethod
    def _summary_answer(
        context: AssistantContext,
    ) -> str:
        """
        Build investigation summary.
        """

        investigation = context.investigation or {}

        title = (
            investigation.get("title")
            or "Investigation"
        )

        status = (
            investigation.get("status")
            or "unknown"
        )

        description = (
            investigation.get("description")
            or ""
        )

        answer = (
            f"{title} is currently recorded "
            f"with status '{status}'."
        )

        if description:
            answer += (
                f" Recorded description: "
                f"{description}"
            )

        answer += (
            f" There are {len(context.memory)} "
            f"recent case-memory entries and "
            f"{len(context.actions)} investigation "
            f"actions available in the retrieved context."
        )

        if context.graph:
            relationships = []

            question = context.metadata.get(
                "query",
                "",
            ).lower()

            for record in context.graph[:10]:

                source = (
                    record.get("value")
                    or "Unknown entity"
                )

                relationship = (
                    record.get("relationship_type")
                    or "relationship"
                )

                target = (
                    record.get("neighbor_value")
                    or "Unknown entity"
                )

                source_match = (
                    str(source).lower() in question
                )

                target_match = (
                    str(target).lower() in question
                )

                if source_match or target_match:

                    relationships.append(
                        f"{source} --{relationship}--> {target}"
                    )

            if not relationships:

                for record in context.graph[:10]:

                    source = (
                        record.get("value")
                        or "Unknown entity"
                    )

                    relationship = (
                        record.get("relationship_type")
                        or "relationship"
                    )

                    target = (
                        record.get("neighbor_value")
                        or "Unknown entity"
                    )

                    relationships.append(
                        f"{source} --{relationship}--> {target}"
                    )

            answer += (
                f" The graph context contains "
                f"{len(context.graph)} retrieved "
                f"relationship record(s)."
            )

            if relationships:

                answer += (
                    " The retrieved graph relationships include: "
                    + "; ".join(relationships)
                    + "."
                )

        return answer

    # ========================================================
    # EVIDENCE
    # ========================================================

    @staticmethod
    def _evidence_answer(
        context: AssistantContext,
    ) -> str:
        """
        Summarize evidence records relevant to the current query.
        """

        if not context.evidence:
            return (
                "No directly relevant evidence records were retrieved "
                "for the current investigation context."
            )

        findings: list[str] = []

        for item in context.evidence[:10]:

            number = (
                item.get("evidence_number")
                or f"Evidence {item.get('id')}"
            )

            title = (
                item.get("title")
                or "Untitled evidence"
            )

            status = (
                item.get("status")
                or "unknown"
            )

            text = str(
                item.get("extracted_text")
                or ""
            ).strip()

            statement = (
                f"{number} "
                f"({title}, status: {status})"
            )

            if text:
                statement += (
                    f": {text}"
                )

            findings.append(statement)

        return (
            "Evidence records relevant to the current query include: "
            + "; ".join(findings)
            + ". The records should be checked against the original source files."
        )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    @staticmethod
    def _relationship_answer(
        context: AssistantContext,
    ) -> str:
        """
        Summarize graph relationships.
        """

        if not context.graph:
            return (
                "No graph relationships were retrieved "
                "for the current investigation context."
            )

        relationships: list[str] = []

        for record in context.graph[:15]:

            source = (
                record.get("value")
                or "Unknown entity"
            )

            relationship = (
                record.get("relationship_type")
                or "relationship"
            )

            target = (
                record.get("neighbor_value")
                or "Unknown entity"
            )

            relationships.append(
                f"{source} --{relationship}--> {target}"
            )

        return (
            "The retrieved graph context shows: "
            + "; ".join(relationships)
            + "."
        )

    # ========================================================
    # PATTERNS
    # ========================================================

    def _pattern_answer(
        self,
        context: AssistantContext,
    ) -> str:
        """
        Return analytical patterns detected from the investigation graph.
        """

        if self.pattern_detector is None:
            return (
                "Pattern analysis is unavailable because "
                "the graph analytics client is not configured."
            )

        investigation = context.investigation or {}

        case_value = (
            investigation.get("case_number")
            or investigation.get("case_value")
        )

        if not case_value:
            return (
                "Pattern analysis could not be performed because "
                "the investigation is not linked to a case identifier."
            )

        try:
            patterns = self.pattern_detector.detect_case_patterns(
                case_value=case_value
            )

            if not patterns:
                patterns = self.pattern_detector.detect_all(
                    limit=20
                )

        except Exception as exc:
            return (
                "Pattern analysis could not be completed: "
                f"{exc}"
            )

        if not patterns:
            return (
                f"No analytical patterns were detected for "
                f"case '{case_value}'."
            )

        statements: list[str] = []

        for pattern in patterns[:10]:

            pattern_type = getattr(
                pattern,
                "pattern_type",
                "UNKNOWN",
            )

            title = getattr(
                pattern,
                "title",
                "Analytical pattern",
            )

            description = getattr(
                pattern,
                "description",
                "",
            )

            confidence = getattr(
                pattern,
                "confidence",
                None,
            )

            severity = getattr(
                pattern,
                "severity",
                None,
            )

            statement = (
                f"{title}: {description}"
            )

            if confidence is not None:
                statement += (
                    f" Confidence {float(confidence):.2f}."
                )

            if severity:
                statement += (
                    f" Severity: {severity}."
                )

            statements.append(
                f"{pattern_type}: {statement}"
            )

        return (
            f"Analytical patterns detected for case "
            f"'{case_value}': "
            + " ".join(statements)
            + " These are structural analytical signals "
            "and should be verified against the underlying "
            "evidence."
        )

    # ========================================================
    # RISK
    # ========================================================

    def _risk_answer(
        self,
        context: AssistantContext,
    ) -> str:
        """
        Return the explainable risk assessment for the investigation
        or focused entity.
        """

        # ----------------------------------------------------
        # Focused entity risk
        # ----------------------------------------------------

        if (
            context.entity
            and context.entity.get("risk_score") is not None
        ):
            score = context.entity["risk_score"]

            name = (
                context.entity.get("name")
                or "The focused entity"
            )

            return (
                f"{name} has a recorded entity risk score "
                f"of {score}/100. "
                "This is an analytical prioritization signal, "
                "not a determination of guilt or criminal responsibility."
            )

        # ----------------------------------------------------
        # Case-level risk
        # ----------------------------------------------------

        if self.risk_engine is None:
            return (
                "Risk analysis is unavailable because "
                "the graph analytics client is not configured."
            )

        investigation = context.investigation or {}

        case_value = (
            investigation.get("case_number")
            or investigation.get("case_value")
        )

        if not case_value:
            return (
                "Risk analysis could not be performed because "
                "the investigation is not linked to a case identifier."
            )

        try:
            assessment = self.risk_engine.assess_case(
                case_value=case_value
            )

        except Exception as exc:
            return (
                "Risk analysis could not be completed: "
                f"{exc}"
            )

        if assessment is None:
            return (
                f"No risk assessment could be generated for "
                f"case '{case_value}'."
            )

        score = float(
            getattr(
                assessment,
                "score",
                0.0,
            )
            or 0.0
        )

        level = (
            getattr(
                assessment,
                "level",
                "unknown",
            )
            or "unknown"
        )

        explanation = (
            getattr(
                assessment,
                "explanation",
                "",
            )
            or ""
        ).strip()

        signals = getattr(
            assessment,
            "signals",
            [],
        ) or []

        answer = (
            f"Current analytical risk for case "
            f"'{case_value}' is {level} "
            f"with a score of {score:.4f}."
        )

        if explanation:
            answer += f" {explanation}"

        if signals:

            answer += (
                " Risk signals considered include:"
            )

            signal_text: list[str] = []

            for signal in signals[:10]:

                name = getattr(
                    signal,
                    "name",
                    "signal",
                )

                value = getattr(
                    signal,
                    "value",
                    None,
                )

                if value is None:
                    signal_text.append(
                        str(name)
                    )

                else:
                    signal_text.append(
                        f"{name}={float(value):.4f}"
                    )

            if signal_text:
                answer += (
                    " "
                    + ", ".join(signal_text)
                    + "."
                )

        answer += (
            " This is an analytical prioritization signal "
            "and is not a determination of guilt or criminal "
            "responsibility."
        )

        return answer

    # ========================================================
    # NEXT STEPS
    # ========================================================

    @staticmethod
    def _next_step_answer(
        context: AssistantContext,
    ) -> str:
        """
        Summarize pending investigation actions.
        """

        pending = [
            action
            for action in context.actions
            if action.get("status")
            in {
                "pending",
                "blocked",
            }
        ]

        if not pending:
            return (
                "No pending or blocked investigation "
                "actions were found in the retrieved context."
            )

        actions: list[str] = []

        for action in pending[:10]:

            title = (
                action.get("title")
                or "Investigation action"
            )

            status = (
                action.get("status")
                or "unknown"
            )

            actions.append(
                f"{title} ({status})"
            )

        return (
            "Recorded pending investigation work includes: "
            + "; ".join(actions)
            + "."
        )

    # ========================================================
    # TIMELINE
    # ========================================================

    @staticmethod
    def _timeline_answer(
        context: AssistantContext,
    ) -> str:
        """
        Summarize timestamped records.
        """

        events: list[tuple[str, str]] = []

        combined = (
            context.search_results
            + context.memory
        )

        for entry in combined:

            timestamp = (
                entry.get("created_at")
                or entry.get("timestamp")
            )

            content = str(
                entry.get(
                    "content",
                    "",
                )
            ).strip()

            if timestamp and content:

                events.append(
                    (
                        str(timestamp),
                        content,
                    )
                )

        events.sort(
            key=lambda item: item[0]
        )

        if not events:
            return (
                "No timestamped records were found "
                "in the retrieved context."
            )

        return (
            "Recorded timeline entries include: "
            + "; ".join(
                f"{timestamp}: {content}"
                for timestamp, content in events[:15]
            )
            + "."
        )

    # ========================================================
    # GENERAL
    # ========================================================

    @staticmethod
    def _general_answer(
        question: str,
        context: AssistantContext,
    ) -> str:
        """
        Build a general evidence-grounded response.
        """

        results = (
            context.search_results
            or context.memory
        )

        if not results:
            return (
                "I could not find directly relevant "
                "information in the available investigation "
                "context for this question."
            )

        statements: list[str] = []

        for entry in results[:10]:

            content = str(
                entry.get(
                    "content",
                    "",
                )
            ).strip()

            if content:
                statements.append(content)

        if not statements:
            return (
                "Relevant records were retrieved, but "
                "they do not contain enough textual "
                "information to answer the question."
            )

        return (
            "Based on the retrieved investigation records, "
            "the relevant information is: "
            + " ".join(statements)
            + "."
        )

    # ========================================================
    # SUPPORTING CONTEXT
    # ========================================================

    @staticmethod
    def _build_supporting_context(
        context: AssistantContext,
    ) -> list[dict[str, Any]]:
        """
        Build compact source references for the response.
        """

        supporting: list[dict[str, Any]] = []

        for evidence in context.evidence[:10]:

            supporting.append(
                {
                    "source_type": "evidence",
                    "source_id": evidence.get("id"),
                    "title": evidence.get("title"),
                    "evidence_number": evidence.get(
                        "evidence_number"
                    ),
                    "status": evidence.get("status"),
                }
            )

        for entry in context.search_results[:10]:

            supporting.append(
                {
                    "source_type": entry.get(
                        "type",
                        "case_memory",
                    ),
                    "source_id": entry.get("id"),
                    "title": entry.get("title"),
                    "source": entry.get("source"),
                }
            )

        if not supporting:

            for entry in context.memory[:10]:

                supporting.append(
                    {
                        "source_type": entry.get(
                            "type",
                            "case_memory",
                        ),
                        "source_id": entry.get("id"),
                        "title": entry.get("title"),
                        "source": entry.get("source"),
                    }
                )

        return supporting

    # ========================================================
    # UNCERTAINTIES
    # ========================================================

    @staticmethod
    def _identify_uncertainties(
        context: AssistantContext,
    ) -> list[str]:
        """
        Identify important limitations in retrieved context.
        """

        uncertainties: list[str] = []

        if not context.search_results:
            uncertainties.append(
                "No query-specific case-memory "
                "records were retrieved."
            )

        if not context.graph:
            uncertainties.append(
                "No graph relationships were available "
                "in the current context."
            )

        if not context.memory:
            uncertainties.append(
                "No case-memory entries were available."
            )

        if not context.actions:
            uncertainties.append(
                "No investigation actions were available."
            )

        uncertainties.append(
            "Retrieved information may be incomplete "
            "and should be checked against source records."
        )

        return uncertainties

    # ========================================================
    # SUGGESTED NEXT STEPS
    # ========================================================

    @staticmethod
    def _suggest_next_steps(
        intent: str,
        context: AssistantContext,
    ) -> list[str]:
        """
        Suggest safe investigative follow-up activities.

        These are suggestions only; the assistant does not
        execute them automatically.
        """

        suggestions: list[str] = []

        if intent == "relationship":

            if context.graph:
                suggestions.append(
                    "Review the underlying source "
                    "records for the identified relationships."
                )
            else:
                suggestions.append(
                    "Identify the relevant entity and "
                    "retrieve its graph relationships."
                )

        elif intent == "evidence":

            suggestions.append(
                "Verify relevant findings against "
                "their original evidence sources."
            )

        elif intent == "pattern":

            suggestions.append(
                "Review the underlying records before "
                "treating an analytical pattern as established."
            )

        elif intent == "next_step":

            suggestions.append(
                "Review pending and blocked actions "
                "with the investigator."
            )

        elif intent == "timeline":

            suggestions.append(
                "Cross-check timestamps against the "
                "original source records."
            )

        else:

            suggestions.append(
                "Review the retrieved records and "
                "identify any missing source information."
            )

        return suggestions

    # ========================================================
    # CONFIDENCE
    # ========================================================

    @staticmethod
    def _calculate_confidence(
        context: AssistantContext,
    ) -> str:
        """
        Estimate response confidence based on retrieval
        coverage, not truthfulness of the underlying evidence.
        """

        search_count = len(
            context.search_results
        )

        memory_count = len(
            context.memory
        )

        graph_count = len(
            context.graph
        )

        total = (
            search_count
            + memory_count
            + graph_count
        )

        if total >= 10:
            return "high"

        if total >= 3:
            return "moderate"

        return "low"

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_question(
        question: str,
    ) -> str:
        """
        Validate and normalize investigator question.
        """

        if not isinstance(question, str):
            raise TypeError(
                "Question must be a string."
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        if len(question) > 4000:
            raise ValueError(
                "Question is too long. "
                "Maximum length is 4000 characters."
            )

        return question


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

# Existing route code imports LocalAssistant.
# Keep both names available so the route does not need
# to be changed.

LocalAssistant = LocalInvestigationAssistant


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def ask_local_assistant(
    session,
    investigation_id: int,
    question: str,
    neo4j_client=None,
) -> AssistantResponse:
    """
    Convenience wrapper for the local assistant.
    """

    assistant = LocalInvestigationAssistant(
        session=session,
        neo4j_client=neo4j_client,
    )

    return assistant.ask(
        investigation_id=investigation_id,
        question=question,
    )
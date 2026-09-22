"""TRINETRA investigation-scoped intelligence report generator."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.analytics.risk_engine import RiskEngine
from app.graph.neo4j_client import Neo4jClient
from app.intelligence.investigation_context import InvestigationContext
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.investigations.action_manager import InvestigationActionManager
from app.investigations.case_memory import CaseMemory


@dataclass
class ReportSection:
    title: str
    content: Any
    section_type: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "section_type": self.section_type,
            "metadata": self.metadata,
        }


@dataclass
class IntelligenceReport:
    report_id: str
    investigation_id: int
    case_id: int | None
    title: str
    generated_at: str
    status: str
    sections: list[ReportSection] = field(default_factory=list)
    risk_assessment: dict[str, Any] | None = None
    executive_summary: str = ""
    limitations: list[str] = field(default_factory=list)
    disclaimer: str = (
        "This report contains analytical and investigative information. "
        "Analytical signals do not constitute a determination of guilt "
        "or criminal responsibility."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "title": self.title,
            "generated_at": self.generated_at,
            "status": self.status,
            "executive_summary": self.executive_summary,
            "sections": [section.to_dict() for section in self.sections],
            "risk_assessment": self.risk_assessment,
            "limitations": self.limitations,
            "disclaimer": self.disclaimer,
        }


class IntelligenceReportGenerator:
    """Build reports from the investigation's explicitly linked evidence."""

    def __init__(self, session, neo4j_client: Neo4jClient | None = None) -> None:
        self.session = session
        self.neo4j_client = neo4j_client
        self.risk_engine = RiskEngine(neo4j_client) if neo4j_client else None
        self.action_manager = InvestigationActionManager(session)
        self.case_memory = CaseMemory(session)

    def generate(
        self,
        investigation_id: int,
        title: str | None = None,
        classification: str = "internal",
        summary: str | None = None,
        include_evidence: bool = True,
        include_entities: bool = True,
        include_relationships: bool = True,
        include_analytics: bool = True,
        include_timeline: bool = True,
        include_actions: bool = True,
        include_memory: bool = True,
        include_risk: bool = True,
    ) -> IntelligenceReport:
        context = InvestigationContext(self.session, investigation_id)
        investigation = context.investigation
        evidence = context.evidence()
        if not evidence and context.case_id is not None:
            # Safe compatibility fallback: only infer case evidence when this
            # case has exactly one investigation. Multiple investigations must
            # use explicit InvestigationEvidence links to avoid cross-scope leaks.
            investigation_count = (
                self.session.query(Investigation)
                .filter(Investigation.case_id == context.case_id)
                .count()
            )
            if investigation_count == 1:
                evidence = (
                    self.session.query(Evidence)
                    .filter(Evidence.case_id == context.case_id)
                    .order_by(Evidence.id.asc())
                    .limit(500)
                    .all()
                )
        entities = context.entities(evidence)
        relationships = context.relationships(evidence)

        sections: list[ReportSection] = [
            ReportSection(
                title="Investigation Overview",
                section_type="overview",
                content=self._investigation_overview(investigation, classification),
            )
        ]

        if include_evidence:
            sections.append(ReportSection(
                title="Investigation Evidence",
                section_type="evidence",
                content=[context.serialize_evidence(item) for item in evidence],
                metadata={"count": len(evidence)},
            ))

        if include_entities:
            sections.append(ReportSection(
                title="Investigation Entities",
                section_type="entities",
                content=[context.serialize_entity(item) for item in entities],
                metadata={"count": len(entities)},
            ))

        if include_relationships:
            sections.append(ReportSection(
                title="Investigation Relationships",
                section_type="relationships",
                content=[context.serialize_relationship(item) for item in relationships],
                metadata={"count": len(relationships)},
            ))

        if include_actions:
            actions = self.action_manager.list_actions(investigation_id)
            sections.append(ReportSection(
                title="Investigation Actions",
                section_type="actions",
                content=actions,
                metadata={"count": len(actions)},
            ))

        if include_memory:
            memory = self.case_memory.get_context(investigation_id, limit=100)
            sections.append(ReportSection(
                title="Case Memory",
                section_type="memory",
                content=memory,
                metadata={"count": len(memory)},
            ))
        else:
            memory = []

        if include_analytics:
            sections.append(ReportSection(
                title="Analytical Scope",
                section_type="analytics",
                content={
                    "evidence_count": len(evidence),
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                    "linked_entity_ids": [entity.id for entity in entities],
                    "linked_evidence_ids": [item.id for item in evidence],
                },
            ))

        if include_timeline:
            sections.append(ReportSection(
                title="Evidence Timeline",
                section_type="timeline",
                content=[self._evidence_timeline_item(item) for item in evidence],
                metadata={"count": len(evidence)},
            ))

        # Investigation-scoped graph summary. SQL is authoritative for scope;
        # Neo4j is supplemental and is never allowed to widen the scope.
        sections.append(ReportSection(
            title="Graph Overview",
            section_type="graph",
            content={
                "available": self.neo4j_client is not None,
                "nodes_in_scope": len(entities),
                "relationships_in_scope": len(relationships),
                "linked_entity_ids": [entity.id for entity in entities],
                "linked_evidence_ids": [item.id for item in evidence],
            },
        ))

        risk = self._generate_risk(entities) if include_risk else None
        if risk is not None:
            sections.append(ReportSection(
                title="Analytical Priority Assessment",
                section_type="risk",
                content=risk,
            ))

        executive_summary = summary.strip() if summary and summary.strip() else self._build_summary(
            investigation, evidence, entities, relationships, risk, memory
        )

        limitations = self._build_limitations(include_risk, self.neo4j_client is not None, len(evidence) == 0)

        return IntelligenceReport(
            report_id=self._build_report_id(investigation_id),
            investigation_id=investigation_id,
            case_id=getattr(investigation, "case_id", None),
            title=title.strip() if title and title.strip() else f"Intelligence Report — {getattr(investigation, 'title', 'Investigation')}",
            generated_at=self._now(),
            status="generated",
            sections=sections,
            risk_assessment=risk,
            executive_summary=executive_summary,
            limitations=limitations,
        )

    @staticmethod
    def _investigation_overview(investigation, classification: str) -> dict[str, Any]:
        return {
            "investigation_id": investigation.id,
            "case_id": investigation.case_id,
            "investigation_number": investigation.investigation_number,
            "title": investigation.title,
            "objective": investigation.objective,
            "status": getattr(investigation.status, "value", investigation.status),
            "outcome": getattr(investigation.outcome, "value", investigation.outcome),
            "investigator": investigation.investigator,
            "investigation_unit": investigation.investigation_unit,
            "classification": classification,
            "findings": investigation.findings,
            "conclusion": investigation.conclusion,
            "created_at": str(investigation.created_at),
            "updated_at": str(investigation.updated_at),
        }

    @staticmethod
    def _evidence_timeline_item(evidence) -> dict[str, Any]:
        return {
            "evidence_id": evidence.id,
            "evidence_number": evidence.evidence_number,
            "title": evidence.title,
            "status": getattr(evidence.status, "value", evidence.status),
            "source_type": evidence.source_type,
            "source_reference": evidence.source_reference,
            "created_at": str(getattr(evidence, "created_at", None)),
        }

    def _generate_risk(self, entities: list[Any]) -> dict[str, Any] | None:
        if not entities:
            return None
        assessments: list[dict[str, Any]] = []
        for entity in entities:
            try:
                assessment = self.risk_engine.assess_entity(
                    entity_type=getattr(entity.entity_type, "value", entity.entity_type),
                    value=entity.name,
                ) if self.risk_engine else None
                if assessment is not None:
                    assessments.append(assessment.to_dict())
            except Exception:
                continue
        if not assessments:
            return None
        scores = [float(item.get("score", item.get("risk_score", 0))) for item in assessments]
        return {
            "scope": "investigation_linked_entities",
            "entity_count": len(assessments),
            "max_score": max(scores),
            "average_score": sum(scores) / len(scores),
            "assessments": assessments,
        }

    @staticmethod
    def _build_summary(investigation, evidence, entities, relationships, risk, memory) -> str:
        status = getattr(investigation.status, "value", investigation.status)
        text = (
            f"Investigation '{investigation.title}' is currently marked as {status}. "
            f"{len(evidence)} evidence item(s), {len(entities)} linked entity/entities, "
            f"and {len(relationships)} evidence-backed relationship(s) are in scope."
        )
        if risk:
            text += f" The highest analytical priority score among linked entities is {risk['max_score']:.2f}."
        text += f" {len(memory)} case-memory entry/entries are available."
        return text

    @staticmethod
    def _build_limitations(include_risk: bool, neo4j_available: bool, no_evidence: bool) -> list[str]:
        limitations = [
            "The report reflects information available at generation time.",
            "Only evidence explicitly linked to this investigation is included in the investigation-scoped evidence sections.",
            "Analytical similarity, pattern, and priority signals require human review.",
            "Absence of a relationship in the current graph does not establish that the relationship does not exist.",
            "Source data quality and completeness may affect analytical results.",
        ]
        if no_evidence:
            limitations.append("No evidence is explicitly linked to this investigation yet.")
        if include_risk:
            limitations.append("Priority scores are analytical signals and are not determinations of guilt.")
        if not neo4j_available:
            limitations.append("Neo4j was not available during report generation, so graph-dependent sections may be absent.")
        return limitations

    @staticmethod
    def _build_report_id(investigation_id: int) -> str:
        return f"IR-{investigation_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


def generate_intelligence_report(session, investigation_id: int, neo4j_client=None) -> IntelligenceReport:
    return IntelligenceReportGenerator(session, neo4j_client).generate(investigation_id)

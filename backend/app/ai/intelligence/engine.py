from __future__ import annotations

from typing import Any

from app.ai.intelligence.analyzer import IntelligenceAnalyzer
from app.ai.intelligence.graph import (
    IntelligenceGraph,
    IntelligenceGraphAnalysis,
)
from app.ai.intelligence.models import IntelligenceResult
from app.ai.intelligence.reasoning import IntelligenceReasoner
from app.ai.intelligence.risk import IntelligenceRiskAnalyzer


# ============================================================
# INTELLIGENCE ENGINE
# ============================================================


class IntelligenceEngine:
    """
    Main intelligence analysis engine.

    Coordinates:

        Investigation data
                ↓
        IntelligenceAnalyzer
                ↓
             Findings
                ↓
        IntelligenceGraph
                ↓
          Graph Analysis
                ↓
        IntelligenceReasoner
                ↓
        Reasoned Findings
                ↓
        IntelligenceRiskAnalyzer
                ↓
        IntelligenceResult
    """

    def __init__(
        self,
        analyzer: IntelligenceAnalyzer | None = None,
        risk_analyzer: IntelligenceRiskAnalyzer | None = None,
        reasoner: IntelligenceReasoner | None = None,
        graph: IntelligenceGraph | None = None,
    ) -> None:

        self.analyzer = (
            analyzer
            if analyzer is not None
            else IntelligenceAnalyzer()
        )

        self.risk_analyzer = (
            risk_analyzer
            if risk_analyzer is not None
            else IntelligenceRiskAnalyzer()
        )

        self.reasoner = (
            reasoner
            if reasoner is not None
            else IntelligenceReasoner()
        )

        self.graph = (
            graph
            if graph is not None
            else IntelligenceGraph()
        )

    # ========================================================
    # ANALYZE INVESTIGATION
    # ========================================================

    def analyze_investigation(
        self,
        *,
        investigation_id: int,
        entities: list[Any],
        evidence: list[Any],
        relationships: list[Any],
    ) -> IntelligenceResult:
        """
        Analyze all available information for an investigation.

        Processing flow:

            1. Analyzer
            2. Graph construction
            3. Graph analysis
            4. Higher-level reasoning
            5. Risk assessment
            6. Summary generation
            7. Final IntelligenceResult
        """

        # ----------------------------------------------------
        # VALIDATE INVESTIGATION
        # ----------------------------------------------------

        if investigation_id <= 0:
            raise ValueError(
                "Investigation ID must be greater than zero."
            )

        # ----------------------------------------------------
        # NORMALIZE INPUT COLLECTIONS
        # ----------------------------------------------------

        entities = list(entities or [])
        evidence = list(evidence or [])
        relationships = list(relationships or [])

        # ----------------------------------------------------
        # STEP 1: ANALYZE INVESTIGATION DATA
        # ----------------------------------------------------

        findings = self.analyzer.analyze(
            entities=entities,
            evidence=evidence,
            relationships=relationships,
        )

        # Analyzer must always produce a list.
        if findings is None:
            findings = []

        # ----------------------------------------------------
        # STEP 2: BUILD INTELLIGENCE GRAPH
        # ----------------------------------------------------

        self.graph.build(
            relationships=relationships,
        )

        # ----------------------------------------------------
        # STEP 3: ANALYZE GRAPH
        # ----------------------------------------------------

        graph_analysis = self.graph.analyze()

        # ----------------------------------------------------
        # STEP 4: HIGHER-LEVEL REASONING
        # ----------------------------------------------------

        findings = self.reasoner.reason(
            findings=findings,
            entities=entities,
            evidence=evidence,
            relationships=relationships,
            graph_analysis=graph_analysis,
        )

        # Reasoner must always produce a list.
        if findings is None:
            findings = []

        # ----------------------------------------------------
        # STEP 5: RISK ASSESSMENT
        # ----------------------------------------------------

        risk_assessment = self.risk_analyzer.assess(
            findings
        )

        # ----------------------------------------------------
        # STEP 6: GENERATE SUMMARY
        # ----------------------------------------------------

        summary = self._generate_summary(
            findings=findings,
            risk_score=risk_assessment.score,
            risk_severity=risk_assessment.severity.value,
            graph_analysis=graph_analysis,
        )

        # ----------------------------------------------------
        # STEP 7: BUILD FINAL RESULT
        # ----------------------------------------------------

        return IntelligenceResult(
            investigation_id=investigation_id,
            findings=findings,
            risk_assessment=risk_assessment,
            summary=summary,
            analyzed_entity_count=len(entities),
            analyzed_evidence_count=len(evidence),
            analyzed_relationship_count=len(
                relationships
            ),
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    def _generate_summary(
        self,
        *,
        findings: list[Any],
        risk_score: float,
        risk_severity: str,
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> str:
        """
        Generate the investigation intelligence summary.
        """

        if not findings:
            summary = (
                "No significant intelligence findings "
                "were detected in the available investigation data."
            )

            if graph_analysis.node_count > 0:
                summary += (
                    f" The intelligence graph contains "
                    f"{graph_analysis.node_count} node(s) and "
                    f"{graph_analysis.edge_count} relationship "
                    f"edge(s)."
                )

            return summary

        summary = (
            f"The intelligence engine identified "
            f"{len(findings)} finding(s). "
            f"The overall assessed risk is "
            f"{risk_severity} "
            f"with a score of {risk_score:.3f}."
        )

        # ----------------------------------------------------
        # GRAPH INFORMATION
        # ----------------------------------------------------

        if graph_analysis.node_count > 0:

            summary += (
                f" The intelligence graph contains "
                f"{graph_analysis.node_count} node(s) and "
                f"{graph_analysis.edge_count} relationship "
                f"edge(s)."
            )

        # ----------------------------------------------------
        # CENTRAL ENTITIES
        # ----------------------------------------------------

        if graph_analysis.central_entities:

            central_ids = ", ".join(
                str(entity_id)
                for entity_id in graph_analysis.central_entities
            )

            summary += (
                f" Central investigation entity/entities: "
                f"{central_ids}."
            )

        # ----------------------------------------------------
        # CONNECTED COMPONENTS
        # ----------------------------------------------------

        if graph_analysis.connected_components:

            component_count = len(
                graph_analysis.connected_components
            )

            summary += (
                f" The graph contains "
                f"{component_count} connected component(s)."
            )

        # ----------------------------------------------------
        # RELATIONSHIP TYPES
        # ----------------------------------------------------

        if graph_analysis.relationship_type_counts:

            relationship_types = ", ".join(
                f"{relationship_type}="
                f"{count}"
                for relationship_type, count
                in sorted(
                    graph_analysis.relationship_type_counts.items()
                )
            )

            summary += (
                f" Relationship type distribution: "
                f"{relationship_types}."
            )

        return summary


# ============================================================
# DEFAULT ENGINE
# ============================================================


intelligence_engine = IntelligenceEngine()
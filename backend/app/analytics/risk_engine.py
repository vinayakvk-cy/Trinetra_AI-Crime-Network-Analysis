"""
TRINETRA Risk Engine
====================

Explainable risk / investigation-priority assessment.

Responsibilities
----------------
- Combine multiple analytical signals
- Produce normalized scores
- Explain why a score was produced
- Separate individual signals from the final score
- Support configurable thresholds

This module does NOT:
- Determine guilt
- Make legal conclusions
- Replace investigators
- Modify Neo4j data
- Extract entities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.analytics.graph_algorithms import GraphAnalytics
from app.analytics.pattern_detector import (
    PatternDetector,
    PatternResult,
)
from app.graph.neo4j_client import Neo4jClient


# ============================================================
# RISK SIGNAL
# ============================================================


@dataclass
class RiskSignal:
    """
    One explainable input contributing to an assessment.
    """

    name: str

    value: float

    weight: float

    contribution: float

    description: str

    source: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert signal to a dictionary.
        """

        return {
            "name": self.name,
            "value": self.value,
            "weight": self.weight,
            "contribution": self.contribution,
            "description": self.description,
            "source": self.source,
            "metadata": self.metadata,
        }


# ============================================================
# RISK ASSESSMENT
# ============================================================


@dataclass
class RiskAssessment:
    """
    Final explainable risk / priority assessment.
    """

    entity_type: str

    entity_value: str

    score: float

    level: str

    signals: list[RiskSignal] = field(
        default_factory=list
    )

    patterns: list[PatternResult] = field(
        default_factory=list
    )

    explanation: str = ""

    disclaimer: str = (
        "This is an analytical prioritization signal "
        "and is not a determination of guilt or "
        "criminal responsibility."
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert assessment to an API-friendly dictionary.
        """

        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "score": self.score,
            "level": self.level,
            "signals": [
                signal.to_dict()
                for signal in self.signals
            ],
            "patterns": [
                pattern.to_dict()
                for pattern in self.patterns
            ],
            "explanation": self.explanation,
            "disclaimer": self.disclaimer,
        }


# ============================================================
# RISK ENGINE
# ============================================================


class RiskEngine:
    """
    Explainable investigation-priority engine.
    """

    # Default weights.
    #
    # These are deliberately modest and transparent.
    # They should be calibrated against real project data
    # before being treated as production thresholds.

    DEFAULT_WEIGHTS = {
        "connectivity": 0.30,
        "relationship_diversity": 0.20,
        "shared_entity": 0.25,
        "pattern_count": 0.15,
        "graph_density": 0.10,
    }

    def __init__(
        self,
        client: Neo4jClient,
        weights: dict[str, float] | None = None,
    ) -> None:

        self.client = client

        self.analytics = GraphAnalytics(
            client
        )

        self.pattern_detector = PatternDetector(
            client
        )

        self.weights = (
            weights
            if weights is not None
            else self.DEFAULT_WEIGHTS.copy()
        )

        self._validate_weights()

    # ========================================================
    # ENTITY ASSESSMENT
    # ========================================================

    def assess_entity(
        self,
        entity_type: str,
        value: str,
    ) -> RiskAssessment | None:
        """
        Generate an explainable assessment for one entity.
        """

        profile = self.analytics.analyze_entity(
            entity_type=entity_type,
            value=value,
        )

        if profile is None:
            return None

        signals: list[RiskSignal] = []

        # ----------------------------------------------------
        # 1. CONNECTIVITY
        # ----------------------------------------------------

        connectivity = (
            self.analytics.connection_score(
                entity_type=entity_type,
                value=value,
            )
        )

        signals.append(
            self._make_signal(
                name="connectivity",
                value=connectivity,
                description=(
                    "Relative graph connectivity "
                    "of the entity."
                ),
                source="graph_analytics",
            )
        )

        # ----------------------------------------------------
        # 2. RELATIONSHIP DIVERSITY
        # ----------------------------------------------------

        diversity = (
            self.analytics.relationship_diversity(
                entity_type=entity_type,
                value=value,
            )
        )

        relationship_type_count = int(
            diversity.get(
                "relationship_types",
                0,
            )
            or 0
        )

        # Normalize diversity.
        #
        # Six relationship categories is treated as a
        # saturation point rather than an absolute truth.

        diversity_score = min(
            relationship_type_count / 6.0,
            1.0,
        )

        signals.append(
            self._make_signal(
                name="relationship_diversity",
                value=diversity_score,
                description=(
                    "Diversity of relationship "
                    "types connected to the entity."
                ),
                source="graph_analytics",
                metadata={
                    "relationship_type_count": (
                        relationship_type_count
                    ),
                    "relationship_types": (
                        diversity.get(
                            "types",
                            [],
                        )
                    ),
                },
            )
        )

        # ----------------------------------------------------
        # 3. SHARED ENTITY SIGNAL
        # ----------------------------------------------------

        shared_score = self._shared_entity_score(
            entity_type=entity_type,
            value=value,
        )

        signals.append(
            self._make_signal(
                name="shared_entity",
                value=shared_score,
                description=(
                    "Signal based on shared entities "
                    "and multi-person connections."
                ),
                source="pattern_detector",
            )
        )

        # ----------------------------------------------------
        # 4. PATTERN SIGNAL
        # ----------------------------------------------------

        patterns = (
            self._detect_entity_patterns(
                entity_type=entity_type,
                value=value,
            )
        )

        pattern_score = min(
            len(patterns) / 4.0,
            1.0,
        )

        signals.append(
            self._make_signal(
                name="pattern_count",
                value=pattern_score,
                description=(
                    "Normalized number of observable "
                    "graph patterns around the entity."
                ),
                source="pattern_detector",
                metadata={
                    "pattern_count": len(
                        patterns
                    )
                },
            )
        )

        # ----------------------------------------------------
        # 5. GRAPH DENSITY
        # ----------------------------------------------------

        density = (
            self.analytics.analyze_neighborhood(
                entity_type=entity_type,
                value=value,
                depth=2,
            )
        )

        density_score = float(
            density.get(
                "density",
                0.0,
            )
            or 0.0
        )

        density_score = max(
            0.0,
            min(
                density_score,
                1.0,
            ),
        )

        signals.append(
            self._make_signal(
                name="graph_density",
                value=density_score,
                description=(
                    "Density of the entity's "
                    "local graph neighborhood."
                ),
                source="graph_analytics",
            )
        )

        # ----------------------------------------------------
        # FINAL SCORE
        # ----------------------------------------------------

        score = self._calculate_score(
            signals
        )

        level = self._score_level(
            score
        )

        explanation = self._build_explanation(
            entity_type=entity_type,
            value=value,
            score=score,
            level=level,
            signals=signals,
            patterns=patterns,
        )

        return RiskAssessment(
            entity_type=entity_type,
            entity_value=value,
            score=score,
            level=level,
            signals=signals,
            patterns=patterns,
            explanation=explanation,
        )

    # ========================================================
    # CASE ASSESSMENT
    # ========================================================

    def assess_case(
        self,
        case_value: str,
    ) -> RiskAssessment | None:
        """
        Assess a case using its connected graph entities.

        The score represents investigation priority based on
        observable graph characteristics.
        """

        entities = (
            self.analytics.queries.get_case_entities(
                case_value=case_value
            )
        )

        if not entities:
            return None

        signals: list[RiskSignal] = []

        # Number of connected entities.
        entity_count = len(entities)

        entity_count_score = min(
            entity_count / 20.0,
            1.0,
        )

        signals.append(
            self._make_signal(
                name="case_entity_count",
                value=entity_count_score,
                description=(
                    "Normalized number of entities "
                    "directly connected to the case."
                ),
                source="graph_queries",
                metadata={
                    "entity_count": entity_count
                },
            )
        )

        # Relationship diversity around the case.
        relationship_types = {
            entity.get(
                "relationship_type"
            )
            for entity in entities
            if entity.get(
                "relationship_type"
            )
        }

        relationship_score = min(
            len(relationship_types) / 6.0,
            1.0,
        )

        signals.append(
            self._make_signal(
                name="case_relationship_diversity",
                value=relationship_score,
                description=(
                    "Diversity of relationship types "
                    "attached to the case."
                ),
                source="graph_queries",
                metadata={
                    "relationship_type_count": (
                        len(relationship_types)
                    ),
                    "relationship_types": sorted(
                        relationship_types
                    ),
                },
            )
        )

        score = self._calculate_case_score(
            signals
        )

        level = self._score_level(
            score
        )

        explanation = (
            f"Case '{case_value}' has "
            f"{entity_count} directly connected "
            f"entities and "
            f"{len(relationship_types)} "
            "relationship types."
        )

        return RiskAssessment(
            entity_type="CASE",
            entity_value=case_value,
            score=score,
            level=level,
            signals=signals,
            patterns=[],
            explanation=explanation,
        )

    # ========================================================
    # SHARED ENTITY SCORE
    # ========================================================

    def _shared_entity_score(
        self,
        entity_type: str,
        value: str,
    ) -> float:
        """
        Calculate a normalized shared-entity signal.
        """

        analysis = (
            self.analytics.shared_entity_analysis(
                entity_type=entity_type,
                value=value,
            )
        )

        people_count = int(
            analysis.get(
                "person_count",
                0,
            )
            or 0
        )

        if people_count <= 1:
            return 0.0

        return min(
            people_count / 5.0,
            1.0,
        )

    # ========================================================
    # ENTITY PATTERNS
    # ========================================================

    def _detect_entity_patterns(
        self,
        entity_type: str,
        value: str,
    ) -> list[PatternResult]:
        """
        Detect patterns relevant to an entity.
        """

        patterns: list[
            PatternResult
        ] = []

        # General connectivity.
        high_connectivity = (
            self.pattern_detector.detect_high_connectivity(
                limit=100,
                minimum_degree=5,
            )
        )

        for pattern in high_connectivity:

            for entity in pattern.entities:

                if (
                    entity.get("type")
                    == entity_type
                    and entity.get("value")
                    == value
                ):
                    patterns.append(
                        pattern
                    )

        # Person-specific patterns.
        if entity_type == "PERSON":

            patterns.extend(
                self.pattern_detector.detect_person_patterns(
                    person_value=value
                )
            )

        # Remove duplicate pattern objects.
        unique: dict[
            tuple[str, str],
            PatternResult,
        ] = {}

        for pattern in patterns:

            key = (
                pattern.pattern_type,
                pattern.title,
            )

            unique[key] = pattern

        return list(
            unique.values()
        )

    # ========================================================
    # SCORE CALCULATION
    # ========================================================

    def _calculate_score(
        self,
        signals: list[RiskSignal],
    ) -> float:
        """
        Calculate weighted normalized score.
        """

        weighted_total = sum(
            signal.contribution
            for signal in signals
        )

        total_weight = sum(
            signal.weight
            for signal in signals
        )

        if total_weight <= 0:
            return 0.0

        score = (
            weighted_total
            / total_weight
        )

        return round(
            max(
                0.0,
                min(
                    score,
                    1.0,
                ),
            ),
            4,
        )

    # ========================================================
    # CASE SCORE
    # ========================================================

    @staticmethod
    def _calculate_case_score(
        signals: list[RiskSignal],
    ) -> float:
        """
        Calculate case-level normalized score.

        Case scoring intentionally uses a simple average because
        case-level calibration should eventually be driven by
        project-specific historical data.
        """

        if not signals:
            return 0.0

        score = sum(
            signal.value
            for signal in signals
        ) / len(signals)

        return round(
            max(
                0.0,
                min(
                    score,
                    1.0,
                ),
            ),
            4,
        )

    # ========================================================
    # CREATE SIGNAL
    # ========================================================

    def _make_signal(
        self,
        name: str,
        value: float,
        description: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> RiskSignal:
        """
        Create a weighted risk signal.
        """

        weight = float(
            self.weights.get(
                name,
                0.0,
            )
        )

        value = max(
            0.0,
            min(
                float(value),
                1.0,
            ),
        )

        contribution = (
            value * weight
        )

        return RiskSignal(
            name=name,
            value=round(
                value,
                4,
            ),
            weight=weight,
            contribution=round(
                contribution,
                4,
            ),
            description=description,
            source=source,
            metadata=metadata or {},
        )

    # ========================================================
    # SCORE LEVEL
    # ========================================================

    @staticmethod
    def _score_level(
        score: float,
    ) -> str:
        """
        Convert normalized score into a priority level.
        """

        if score >= 0.75:
            return "high"

        if score >= 0.50:
            return "medium"

        if score >= 0.25:
            return "low"

        return "minimal"

    # ========================================================
    # EXPLANATION
    # ========================================================

    @staticmethod
    def _build_explanation(
        entity_type: str,
        value: str,
        score: float,
        level: str,
        signals: list[RiskSignal],
        patterns: list[PatternResult],
    ) -> str:
        """
        Build a human-readable explanation.
        """

        active_signals = [
            signal
            for signal in signals
            if signal.value > 0
        ]

        active_signals.sort(
            key=lambda signal: signal.contribution,
            reverse=True,
        )

        explanation = (
            f"{entity_type} '{value}' "
            f"received a {level} analytical "
            f"priority score of {score:.2f}."
        )

        if active_signals:

            top = active_signals[:3]

            reasons = ", ".join(
                signal.name.replace(
                    "_",
                    " ",
                )
                for signal in top
            )

            explanation += (
                f" The strongest contributing "
                f"signals were: {reasons}."
            )

        if patterns:

            explanation += (
                f" {len(patterns)} observable "
                "graph pattern(s) were detected."
            )

        explanation += (
            " This score is an analytical "
            "prioritization aid and should be "
            "reviewed alongside source evidence."
        )

        return explanation

    # ========================================================
    # VALIDATE WEIGHTS
    # ========================================================

    def _validate_weights(
        self,
    ) -> None:
        """
        Validate configured weights.
        """

        for name, weight in self.weights.items():

            if weight < 0:
                raise ValueError(
                    f"Weight '{name}' cannot be negative."
                )

        if sum(self.weights.values()) <= 0:
            raise ValueError(
                "At least one risk weight must be greater than zero."
            )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def assess_entity_risk(
    client: Neo4jClient,
    entity_type: str,
    value: str,
) -> RiskAssessment | None:
    """
    Convenience wrapper for entity assessment.
    """

    engine = RiskEngine(client)

    return engine.assess_entity(
        entity_type=entity_type,
        value=value,
    )


def assess_case_risk(
    client: Neo4jClient,
    case_value: str,
) -> RiskAssessment | None:
    """
    Convenience wrapper for case assessment.
    """

    engine = RiskEngine(client)

    return engine.assess_case(
        case_value=case_value
    )

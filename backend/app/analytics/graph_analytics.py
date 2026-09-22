from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.graph.graph_queries import GraphQueryService


logger = logging.getLogger("trinetra.analytics.graph")


# ============================================================
# INDICATOR TYPES
# ============================================================

INDICATOR_TYPES = {
    "CONNECTIVITY",
    "COMMUNICATION",
    "CROSS_CASE",
    "SHARED_PHONE",
    "SHARED_VEHICLE",
    "TRANSACTION",
    "LOCATION",
    "SOCIAL",
    "EVIDENCE",
    "TEMPORAL",
}


# ============================================================
# PRIORITY LEVELS
# ============================================================

PRIORITY_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL_REVIEW",
}


# ============================================================
# ANALYTICAL INDICATOR
# ============================================================

@dataclass
class AnalyticalIndicator:
    """
    One explainable analytical finding.

    The score represents analytical relevance.
    It is NOT a probability of criminality.
    """

    indicator_id: str
    indicator_type: str
    entity_id: str | None
    case_id: str | None
    score: float
    priority: str
    title: str
    explanation: str
    evidence_count: int = 0
    source_record_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )


# ============================================================
# GRAPH ANALYSIS RESULT
# ============================================================

@dataclass
class GraphAnalysisResult:
    """
    Complete analysis result for a case.
    """

    case_id: str
    indicators: list[AnalyticalIndicator]
    overall_score: float
    priority: str
    summary: str
    graph_statistics: dict[str, Any] = field(
        default_factory=dict
    )
    generated_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to a JSON-compatible dictionary.
        """

        return {
            "case_id": self.case_id,
            "indicators": [
                asdict(indicator)
                for indicator in self.indicators
            ],
            "overall_score": self.overall_score,
            "priority": self.priority,
            "summary": self.summary,
            "graph_statistics": self.graph_statistics,
            "generated_at": self.generated_at,
        }


# ============================================================
# GRAPH ANALYTICS ENGINE
# ============================================================

class GraphAnalyticsEngine:
    """
    Main graph analytics service.
    """

    def __init__(
        self,
        graph_queries: GraphQueryService,
    ) -> None:
        self.graph = graph_queries

    # ========================================================
    # FULL CASE ANALYSIS
    # ========================================================

    def analyze_case(
        self,
        case_id: str,
    ) -> GraphAnalysisResult:
        """
        Run all available graph analysis modules for a case.
        """

        indicators: list[AnalyticalIndicator] = []

        indicators.extend(
            self.analyze_cross_case(case_id)
        )

        indicators.extend(
            self.analyze_shared_phones(case_id)
        )

        indicators.extend(
            self.analyze_shared_vehicles(case_id)
        )

        indicators.extend(
            self.analyze_case_entities(case_id)
        )

        overall_score = self.calculate_overall_score(
            indicators
        )

        priority = self.score_to_priority(
            overall_score
        )

        summary = self.generate_summary(
            indicators,
            overall_score,
            priority,
        )

        try:
            statistics = self.graph.get_entity_counts()
            case_statistics = (
                self.graph.get_case_graph_statistics(
                    case_id
                )
            )

        except Exception:
            logger.exception(
                "Unable to retrieve graph statistics"
            )
            statistics = []
            case_statistics = {
                "node_count": 0,
                "relationship_count": 0,
            }

        graph_statistics = {
            "entity_counts": statistics,
            "node_count": case_statistics["node_count"],
            "relationship_count": case_statistics[
                "relationship_count"
            ],
        }

        return GraphAnalysisResult(
            case_id=case_id,
            indicators=indicators,
            overall_score=overall_score,
            priority=priority,
            summary=summary,
            graph_statistics=graph_statistics,
        )

    # ========================================================
    # CROSS CASE
    # ========================================================

    def analyze_cross_case(
        self,
        case_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Identify entities associated with the current case
        that are also associated with other cases.
        """

        results = self.graph.find_cross_case_entities(
            case_id
        )

        indicators: list[AnalyticalIndicator] = []

        for index, result in enumerate(results):
            entity = result.get("entity", {})
            other_case = result.get("other_case", {})

            entity_id = self._node_id(entity)
            other_case_id = self._node_id(other_case)

            if not entity_id:
                continue

            indicator_id = (
                f"cross-case-{case_id}-"
                f"{entity_id}-{index}"
            )

            indicators.append(
                AnalyticalIndicator(
                    indicator_id=indicator_id,
                    indicator_type="CROSS_CASE",
                    entity_id=entity_id,
                    case_id=case_id,
                    score=0.75,
                    priority="HIGH",
                    title="Cross-case entity association",
                    explanation=(
                        "The entity connected to this case "
                        "also appears connected to another "
                        "case. This association should be "
                        "reviewed against the underlying "
                        "records and dates."
                    ),
                    evidence_count=1,
                    metadata={
                        "other_case_id": other_case_id
                    },
                )
            )

        return indicators

    # ========================================================
    # SHARED PHONES
    # ========================================================

    def analyze_shared_phones(
        self,
        case_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Identify phones appearing across cases.
        """

        results = self.graph.find_shared_phones(
            case_id
        )

        indicators: list[AnalyticalIndicator] = []

        for index, result in enumerate(results):
            phone = result.get("phone", {})
            other_case = result.get("other_case", {})

            phone_id = self._node_id(phone)
            other_case_id = self._node_id(other_case)

            if not phone_id:
                continue

            indicators.append(
                AnalyticalIndicator(
                    indicator_id=(
                        f"shared-phone-"
                        f"{case_id}-"
                        f"{phone_id}-"
                        f"{index}"
                    ),
                    indicator_type="SHARED_PHONE",
                    entity_id=phone_id,
                    case_id=case_id,
                    score=0.70,
                    priority="HIGH",
                    title=(
                        "Phone associated with multiple cases"
                    ),
                    explanation=(
                        "A phone node associated with "
                        "this case is also associated "
                        "with another case. Verify "
                        "ownership, subscriber information, "
                        "dates and call records."
                    ),
                    evidence_count=1,
                    metadata={
                        "other_case_id": other_case_id
                    },
                )
            )

        return indicators

    # ========================================================
    # SHARED VEHICLES
    # ========================================================

    def analyze_shared_vehicles(
        self,
        case_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Identify vehicles appearing across cases.
        """

        results = self.graph.find_shared_vehicles(
            case_id
        )

        indicators: list[AnalyticalIndicator] = []

        for index, result in enumerate(results):
            vehicle = result.get("vehicle", {})
            other_case = result.get("other_case", {})

            vehicle_id = self._node_id(vehicle)
            other_case_id = self._node_id(other_case)

            if not vehicle_id:
                continue

            indicators.append(
                AnalyticalIndicator(
                    indicator_id=(
                        f"shared-vehicle-"
                        f"{case_id}-"
                        f"{vehicle_id}-"
                        f"{index}"
                    ),
                    indicator_type="SHARED_VEHICLE",
                    entity_id=vehicle_id,
                    case_id=case_id,
                    score=0.65,
                    priority="MEDIUM",
                    title=(
                        "Vehicle associated with multiple cases"
                    ),
                    explanation=(
                        "A vehicle associated with this "
                        "case also appears in another case. "
                        "Verify ownership, usage and the "
                        "relevant dates."
                    ),
                    evidence_count=1,
                    metadata={
                        "other_case_id": other_case_id
                    },
                )
            )

        return indicators

    # ========================================================
    # CASE ENTITY ANALYSIS
    # ========================================================

    def analyze_case_entities(
        self,
        case_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Analyze entities directly connected to a case.

        High connectivity is surfaced as an investigation
        indicator, not as evidence of wrongdoing.
        """

        results = self.graph.get_case_entities(
            case_id
        )

        indicators: list[AnalyticalIndicator] = []

        for index, result in enumerate(results):
            entity = result

            entity_id = self._node_id(entity)

            if not entity_id:
                continue

            degree_result = self.graph.get_entity_degree(
                entity_id
            )

            degree = 0

            if degree_result:
                degree = int(
                    degree_result[0].get(
                        "degree",
                        0,
                    )
                )

            if degree < 3:
                continue

            score = min(
                degree / 20.0,
                1.0,
            )

            priority = self.score_to_priority(
                score
            )

            indicators.append(
                AnalyticalIndicator(
                    indicator_id=(
                        f"connectivity-"
                        f"{case_id}-"
                        f"{entity_id}-"
                        f"{index}"
                    ),
                    indicator_type="CONNECTIVITY",
                    entity_id=entity_id,
                    case_id=case_id,
                    score=round(score, 4),
                    priority=priority,
                    title="Highly connected graph entity",
                    explanation=(
                        "This entity has a relatively "
                        "large number of direct graph "
                        "connections. Review the underlying "
                        "relationships to determine their "
                        "meaning and relevance."
                    ),
                    evidence_count=degree,
                    metadata={
                        "degree": degree
                    },
                )
            )

        return indicators

    # ========================================================
    # COMMUNICATION ANALYSIS
    # ========================================================

    def analyze_communication(
        self,
        phone_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Analyze the communication network around a phone.
        """

        results = self.graph.get_phone_network(
            phone_id
        )

        connection_count = len(results)

        if connection_count == 0:
            return []

        score = min(
            connection_count / 20.0,
            1.0,
        )

        return [
            AnalyticalIndicator(
                indicator_id=(
                    f"communication-{phone_id}"
                ),
                indicator_type="COMMUNICATION",
                entity_id=phone_id,
                case_id=None,
                score=round(score, 4),
                priority=self.score_to_priority(
                    score
                ),
                title="Communication network detected",
                explanation=(
                    "The phone is connected to "
                    "multiple communication entities "
                    "in the graph. Review call records, "
                    "timestamps and contextual evidence."
                ),
                evidence_count=connection_count,
                metadata={
                    "connection_count": connection_count
                },
            )
        ]

    # ========================================================
    # LOCATION ANALYSIS
    # ========================================================

    def analyze_locations(
        self,
        entity_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Analyze location associations.

        Location presence alone must not be interpreted
        as proof of involvement.
        """

        results = self.graph.get_entity_locations(
            entity_id
        )

        if not results:
            return []

        return [
            AnalyticalIndicator(
                indicator_id=f"location-{entity_id}",
                indicator_type="LOCATION",
                entity_id=entity_id,
                case_id=None,
                score=min(
                    len(results) / 10.0,
                    1.0,
                ),
                priority="MEDIUM",
                title="Location history available",
                explanation=(
                    "Location records are available "
                    "for this entity. Investigators "
                    "should verify timestamps, accuracy "
                    "and source reliability."
                ),
                evidence_count=len(results),
                metadata={
                    "location_count": len(results)
                },
            )
        ]

    # ========================================================
    # TRANSACTION ANALYSIS
    # ========================================================

    def analyze_transactions(
        self,
        account_id: str,
    ) -> list[AnalyticalIndicator]:
        """
        Analyze account transaction connectivity.
        """

        results = self.graph.get_transaction_network(
            account_id
        )

        connection_count = len(results)

        if connection_count == 0:
            return []

        score = min(
            connection_count / 20.0,
            1.0,
        )

        return [
            AnalyticalIndicator(
                indicator_id=(
                    f"transaction-{account_id}"
                ),
                indicator_type="TRANSACTION",
                entity_id=account_id,
                case_id=None,
                score=round(score, 4),
                priority=self.score_to_priority(
                    score
                ),
                title="Connected transaction network",
                explanation=(
                    "The account has connections "
                    "to multiple accounts in the "
                    "transaction graph. Review transaction "
                    "dates, amounts, counterparties and "
                    "case context."
                ),
                evidence_count=connection_count,
                metadata={
                    "connection_count": connection_count
                },
            )
        ]

    # ========================================================
    # CONNECTION PATH
    # ========================================================

    def analyze_connection(
        self,
        source_entity_id: str,
        target_entity_id: str,
    ) -> dict[str, Any]:
        """
        Find graph paths between two entities.
        """

        paths = self.graph.find_connection(
            source_entity_id,
            target_entity_id,
        )

        return {
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "paths_found": len(paths),
            "paths": paths,
        }

    # ========================================================
    # OVERALL SCORE
    # ========================================================

    @staticmethod
    def calculate_overall_score(
        indicators: list[AnalyticalIndicator],
    ) -> float:
        """
        Calculate an aggregate investigation-priority
        indicator.

        This is NOT a probability of criminality.
        """

        if not indicators:
            return 0.0

        scores = sorted(
            (
                indicator.score
                for indicator in indicators
            ),
            reverse=True,
        )

        strongest = scores[:10]

        if not strongest:
            return 0.0

        weights = [
            1.0 / (index + 1)
            for index in range(len(strongest))
        ]

        weighted_score = (
            sum(
                score * weight
                for score, weight in zip(
                    strongest,
                    weights,
                )
            )
            / sum(weights)
        )

        return round(
            min(
                weighted_score,
                1.0,
            ),
            4,
        )

    # ========================================================
    # SCORE -> PRIORITY
    # ========================================================

    @staticmethod
    def score_to_priority(
        score: float,
    ) -> str:

        if score >= 0.85:
            return "CRITICAL_REVIEW"

        if score >= 0.65:
            return "HIGH"

        if score >= 0.40:
            return "MEDIUM"

        return "LOW"

    # ========================================================
    # SUMMARY
    # ========================================================

    @staticmethod
    def generate_summary(
        indicators: list[AnalyticalIndicator],
        overall_score: float,
        priority: str,
    ) -> str:
        """
        Generate a concise human-readable summary.
        """

        if not indicators:
            return (
                "No significant graph indicators "
                "were identified from the currently "
                "available data."
            )

        type_counts: dict[str, int] = {}

        for indicator in indicators:
            type_counts[
                indicator.indicator_type
            ] = (
                type_counts.get(
                    indicator.indicator_type,
                    0,
                )
                + 1
            )

        categories = ", ".join(
            (
                f"{key}: {value}"
                for key, value in type_counts.items()
            )
        )

        return (
            f"The graph analysis produced "
            f"{len(indicators)} analytical "
            f"indicator(s). "
            f"Aggregate review priority: "
            f"{priority} "
            f"(indicator score "
            f"{overall_score:.2f}). "
            f"Categories: {categories}. "
            f"These results require investigator "
            f"review and should be evaluated against "
            f"the underlying evidence."
        )

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @staticmethod
    def indicators_to_dict(
        indicators: list[AnalyticalIndicator],
    ) -> list[dict[str, Any]]:

        return [
            asdict(indicator)
            for indicator in indicators
        ]

    # ========================================================
    # NODE ID HELPER
    # ========================================================

    @staticmethod
    def _node_id(
        node: Any,
    ) -> str | None:
        """
        Extract a Neo4j entity ID from a graph result.
        """

        if not node:
            return None

        if isinstance(node, dict):
            # GraphQueries commonly returns Neo4j element IDs
            # under the "node_id" field.
            value = node.get("node_id")

            if value is not None:
                return str(value)

            # Support generic "id" fields as well.
            value = node.get("id")

            if value is not None:
                return str(value)

            # Support Neo4j-style nested properties.
            properties = node.get("properties")

            if isinstance(properties, dict):
                value = properties.get("node_id")

                if value is not None:
                    return str(value)

                value = properties.get("id")

                if value is not None:
                    return str(value)

        return None

# ============================================================
# FACTORY
# ============================================================

def create_graph_analytics_engine(
    graph_queries: GraphQueryService,
) -> GraphAnalyticsEngine:
    """
    Create a graph analytics engine.
    """

    return GraphAnalyticsEngine(
        graph_queries
    )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

GraphAnalytics = GraphAnalyticsEngine
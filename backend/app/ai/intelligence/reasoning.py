from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.ai.intelligence.graph import (
    IntelligenceGraph,
    IntelligenceGraphAnalysis,
)
from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceSeverity,
)


class IntelligenceReasoner:
    """
    Higher-level graph/intelligence reasoning layer.

    The reasoner preserves the original detector findings and adds
    second-order findings derived from combinations of:

      - relationship concentration
      - confidence reinforcement
      - evidence reinforcement
      - graph centrality / clusters
      - indirect and reinforced paths
      - relationship-type convergence
      - hub-and-spoke structure
      - articulation/bridge entities
      - triangles / closed motifs
      - reciprocal relationships
      - repeated relationship types
      - centrality + multiple independent signals

    Important design rule:

        A graph pattern is described as an observed structural pattern.
        It does not by itself assert criminality, intent, causation, or
        a direct relationship that is not present in the source data.
    """

    HIGH_CONFIDENCE = 0.80

    # ========================================================
    # MAIN REASONING
    # ========================================================

    def reason(
        self,
        *,
        findings: list[IntelligenceFinding],
        entities: list[Any],
        evidence: list[Any],
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        if not findings:
            return []

        reasoned: list[IntelligenceFinding] = list(findings)

        reasoned.extend(
            self._reason_entity_activity(
                findings=findings,
                entities=entities,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_relationship_patterns(
                findings=findings,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_multiple_high_confidence_findings(
                findings=findings,
            )
        )

        reasoned.extend(
            self._reason_evidence_reinforcement(
                findings=findings,
                evidence=evidence,
            )
        )

        reasoned.extend(
            self._reason_graph_centrality(
                findings=findings,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_graph_components(
                findings=findings,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_graph_structure(
                findings=findings,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_indirect_relationships(
                findings=findings,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_central_reinforcement(
                findings=findings,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_compound_graph_pattern(
                findings=findings,
                relationships=relationships,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_hub_and_spoke(
                findings=findings,
                relationships=relationships,
                graph_analysis=graph_analysis,
            )
        )

        # Keep _reason_bridge_entities() as a compatibility wrapper,
        # but do not call it here because it delegates to the same
        # articulation-point detector called below.
        reasoned.extend(
            self._reason_reinforced_multi_hop_paths(
                findings=findings,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_relationship_convergence(
                findings=findings,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_central_cluster(
                findings=findings,
                graph_analysis=graph_analysis,
            )
        )

        # ====================================================
        # STRONGER GRAPH MOTIFS
        # ====================================================

        reasoned.extend(
            self._reason_reciprocal_relationships(
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_repeated_relationships(
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_triangles(
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_articulation_points(
                relationships=relationships,
                graph_analysis=graph_analysis,
            )
        )

        reasoned.extend(
            self._reason_typed_path_reinforcement(
                findings=findings,
                relationships=relationships,
            )
        )

        reasoned.extend(
            self._reason_independent_signal_convergence(
                findings=findings,
                relationships=relationships,
                graph_analysis=graph_analysis,
            )
        )

        return self._remove_duplicates(reasoned)

    # ========================================================
    # BASIC ENTITY / RELATIONSHIP HELPERS
    # ========================================================

    @staticmethod
    def _relationship_endpoints(
        relationship: Any,
    ) -> tuple[int | None, int | None]:

        return (
            IntelligenceReasoner._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            ),
            IntelligenceReasoner._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            ),
        )

    @staticmethod
    def _relationship_type(
        relationship: Any,
    ) -> str | None:

        value = getattr(
            relationship,
            "relationship_type",
            None,
        )

        if value is None:
            return None

        return str(
            getattr(
                value,
                "value",
                value,
            )
        )

    @staticmethod
    def _relationship_id(
        relationship: Any,
    ) -> int | None:

        return IntelligenceReasoner._safe_int(
            getattr(
                relationship,
                "id",
                None,
            )
        )

    @classmethod
    def _build_adjacency(
        cls,
        relationships: list[Any],
    ) -> dict[int, set[int]]:

        adjacency: dict[int, set[int]] = defaultdict(set)

        for relationship in relationships:
            source_id, target_id = cls._relationship_endpoints(
                relationship
            )

            if source_id is None or target_id is None:
                continue

            if source_id == target_id:
                adjacency[source_id].add(target_id)
                continue

            # Treat the investigation graph as connected/undirected
            # for structural reasoning. Direction/type are retained
            # separately where they matter.
            adjacency[source_id].add(target_id)
            adjacency[target_id].add(source_id)

        return dict(adjacency)

    @classmethod
    def _neighbors(
        cls,
        relationships: list[Any],
        entity_id: int,
    ) -> set[int]:

        adjacency = cls._build_adjacency(
            relationships
        )

        return adjacency.get(
            entity_id,
            set(),
        )

    @classmethod
    def _edge_ids_between(
        cls,
        relationships: list[Any],
        entity_a: int,
        entity_b: int,
    ) -> list[int]:

        result: list[int] = []

        for relationship in relationships:
            source_id, target_id = cls._relationship_endpoints(
                relationship
            )

            if {
                source_id,
                target_id,
            } != {
                entity_a,
                entity_b,
            }:
                continue

            relationship_id = cls._relationship_id(
                relationship
            )

            if relationship_id is not None:
                result.append(
                    relationship_id
                )

        return list(
            dict.fromkeys(result)
        )

    @classmethod
    def _path_edges(
        cls,
        relationships: list[Any],
        path: list[int],
    ) -> list[int]:

        ids: list[int] = []

        for left, right in zip(
            path,
            path[1:],
        ):
            ids.extend(
                cls._edge_ids_between(
                    relationships,
                    left,
                    right,
                )
            )

        return list(
            dict.fromkeys(ids)
        )

    @classmethod
    def _finding_entities(
        cls,
        finding: IntelligenceFinding,
    ) -> set[int]:

        return set(
            cls._safe_int_list(
                finding.supporting_entity_ids
            )
        )

    # ========================================================
    # 1. ENTITY ACTIVITY
    # ========================================================

    def _reason_entity_activity(
        self,
        *,
        findings: list[IntelligenceFinding],
        entities: list[Any],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if not relationships:
            return []

        entity_counter: Counter[int] = Counter()
        related: dict[int, set[int]] = defaultdict(set)
        relation_ids: dict[int, list[int]] = defaultdict(list)

        for relationship in relationships:
            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_id = self._relationship_id(
                relationship
            )

            if source_id is not None:
                entity_counter[source_id] += 1

                if target_id is not None:
                    related[source_id].add(
                        target_id
                    )

                if relationship_id is not None:
                    relation_ids[source_id].append(
                        relationship_id
                    )

            if target_id is not None:
                entity_counter[target_id] += 1

                if source_id is not None:
                    related[target_id].add(
                        source_id
                    )

                if relationship_id is not None:
                    relation_ids[target_id].append(
                        relationship_id
                    )

        generated: list[IntelligenceFinding] = []

        for entity_id, count in entity_counter.items():

            if count < 2:
                continue

            confidence = min(
                0.60 + count * 0.05,
                0.90,
            )

            generated.append(
                IntelligenceFinding(
                    title="Entity activity concentration",
                    description=(
                        f"Entity {entity_id} participates in "
                        f"{count} relationship record(s), indicating "
                        f"concentrated activity within the investigation."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if count >= 5
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id,
                        *sorted(
                            related[entity_id]
                        ),
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids[entity_id]
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 2. MULTIPLE RELATIONSHIP TYPES BETWEEN SAME PAIR
    # ========================================================

    def _reason_relationship_patterns(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if not relationships:
            return []

        pair_types: dict[
            tuple[int, int],
            set[str],
        ] = defaultdict(set)

        pair_ids: dict[
            tuple[int, int],
            list[int],
        ] = defaultdict(list)

        for relationship in relationships:

            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_type = self._relationship_type(
                relationship
            )

            relationship_id = self._relationship_id(
                relationship
            )

            if (
                source_id is None
                or target_id is None
                or relationship_type is None
            ):
                continue

            pair = tuple(
                sorted(
                    (
                        source_id,
                        target_id,
                    )
                )
            )

            pair_types[pair].add(
                relationship_type
            )

            if relationship_id is not None:
                pair_ids[pair].append(
                    relationship_id
                )

        generated: list[IntelligenceFinding] = []

        for (
            source_id,
            target_id,
        ), types in pair_types.items():

            if len(types) < 2:
                continue

            generated.append(
                IntelligenceFinding(
                    title="Multiple relationship indicators",
                    description=(
                        f"Entities {source_id} and {target_id} are "
                        f"connected through multiple relationship types: "
                        f"{', '.join(sorted(types))}."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if len(types) >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.65 + len(types) * 0.08,
                            0.92,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            pair_ids[
                                (
                                    source_id,
                                    target_id,
                                )
                            ]
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 3. MULTIPLE HIGH-CONFIDENCE FINDINGS
    # ========================================================

    def _reason_multiple_high_confidence_findings(
        self,
        *,
        findings: list[IntelligenceFinding],
    ) -> list[IntelligenceFinding]:

        counts: Counter[int] = Counter()

        relation_ids: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for finding in findings:

            if finding.confidence < self.HIGH_CONFIDENCE:
                continue

            for entity_id in self._safe_int_list(
                finding.supporting_entity_ids
            ):
                counts[entity_id] += 1

                relation_ids[entity_id].extend(
                    self._safe_int_list(
                        finding.supporting_relationship_ids
                    )
                )

        generated: list[IntelligenceFinding] = []

        for entity_id, count in counts.items():

            if count < 2:
                continue

            generated.append(
                IntelligenceFinding(
                    title="Multiple high-confidence indicators",
                    description=(
                        f"Entity {entity_id} appears in {count} "
                        f"high-confidence intelligence finding(s), "
                        f"indicating multiple independent indicators "
                        f"associated with the entity."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if count >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.70 + count * 0.05,
                            0.95,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids[entity_id]
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 4. EVIDENCE REINFORCEMENT
    # ========================================================

    def _reason_evidence_reinforcement(
        self,
        *,
        findings: list[IntelligenceFinding],
        evidence: list[Any],
    ) -> list[IntelligenceFinding]:

        if not evidence:
            return []

        evidence_ids = {
            self._safe_int(
                getattr(
                    item,
                    "id",
                    None,
                )
            )
            for item in evidence
        }

        evidence_ids.discard(None)

        counts: Counter[int] = Counter()

        evidence_entities: dict[
            int,
            set[int],
        ] = defaultdict(set)

        evidence_relations: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for finding in findings:

            for evidence_id in self._safe_int_list(
                finding.supporting_evidence_ids
            ):

                if evidence_id not in evidence_ids:
                    continue

                counts[evidence_id] += 1

                evidence_entities[evidence_id].update(
                    self._safe_int_list(
                        finding.supporting_entity_ids
                    )
                )

                evidence_relations[evidence_id].extend(
                    self._safe_int_list(
                        finding.supporting_relationship_ids
                    )
                )

        generated: list[IntelligenceFinding] = []

        for evidence_id, count in counts.items():

            if count < 2:
                continue

            generated.append(
                IntelligenceFinding(
                    title="Evidence reinforcement detected",
                    description=(
                        f"Evidence record {evidence_id} supports "
                        f"{count} intelligence finding(s), providing "
                        f"reinforcing support for the associated activity."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if count >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.70 + count * 0.06,
                            0.95,
                        ),
                        3,
                    ),
                    supporting_entity_ids=sorted(
                        evidence_entities[evidence_id]
                    ),
                    supporting_evidence_ids=[
                        evidence_id
                    ],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            evidence_relations[evidence_id]
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 5. CENTRALITY
    # ========================================================

    def _reason_graph_centrality(
        self,
        *,
        findings: list[IntelligenceFinding],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        if (
            not graph_analysis.central_entities
            or graph_analysis.node_count < 2
        ):
            return []

        generated: list[IntelligenceFinding] = []

        for entity_id in graph_analysis.central_entities:

            connected_indicators = sum(
                1
                for finding in findings
                if entity_id in self._finding_entities(
                    finding
                )
            )

            generated.append(
                IntelligenceFinding(
                    title="Graph central entity detected",
                    description=(
                        f"Entity {entity_id} is identified as a "
                        f"central entity in the investigation relationship "
                        f"graph. Its position indicates concentrated "
                        f"connectivity with other investigation entities."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if connected_indicators >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.72 + connected_indicators * 0.04,
                            0.92,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=[],
                )
            )

        return generated

    # ========================================================
    # 6. COMPONENTS
    # ========================================================

    def _reason_graph_components(
        self,
        *,
        findings: list[IntelligenceFinding],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        generated: list[IntelligenceFinding] = []

        for component in (
            graph_analysis.connected_components
            or []
        ):
            component_ids = self._safe_int_list(
                component
            )

            if len(component_ids) < 3:
                continue

            generated.append(
                IntelligenceFinding(
                    title="Connected intelligence cluster",
                    description=(
                        f"A connected intelligence cluster containing "
                        f"{len(component_ids)} entities was detected: "
                        f"{', '.join(map(str, component_ids))}."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if len(component_ids) >= 5
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.65
                            + len(component_ids) * 0.04,
                            0.90,
                        ),
                        3,
                    ),
                    supporting_entity_ids=component_ids,
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=[],
                )
            )

        return generated

    # ========================================================
    # 7. GRAPH STRUCTURE
    # ========================================================

    def _reason_graph_structure(
        self,
        *,
        findings: list[IntelligenceFinding],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        node_count = graph_analysis.node_count
        edge_count = graph_analysis.edge_count

        if node_count < 3 or edge_count < 2:
            return []

        average_degree = (
            edge_count * 2
        ) / node_count

        if average_degree < 1.5:
            return []

        return [
            IntelligenceFinding(
                title="Dense relationship network",
                description=(
                    f"The investigation graph contains {node_count} "
                    f"entities and {edge_count} relationship edge(s), "
                    f"producing an average degree of "
                    f"{average_degree:.2f}. This indicates a relatively "
                    f"concentrated relationship network."
                ),
                severity=(
                    IntelligenceSeverity.HIGH
                    if average_degree >= 3.0
                    else IntelligenceSeverity.MEDIUM
                ),
                confidence=round(
                    min(
                        0.68
                        + average_degree * 0.05,
                        0.92,
                    ),
                    3,
                ),
                supporting_entity_ids=list(
                    self._safe_int_list(
                        graph_analysis.central_entities
                    )
                ),
                supporting_evidence_ids=[],
                supporting_relationship_ids=[],
            )
        ]

    # ========================================================
    # 8. INDIRECT RELATIONSHIPS
    # ========================================================

    def _reason_indirect_relationships(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        graph = IntelligenceGraph()

        graph.build(
            relationships=relationships
        )

        if len(graph.nodes) < 3:
            return []

        generated: list[IntelligenceFinding] = []

        entity_ids = sorted(
            graph.nodes.keys()
        )

        for index, source_id in enumerate(
            entity_ids
        ):
            for target_id in entity_ids[
                index + 1:
            ]:

                path_result = graph.find_path(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                )

                if (
                    path_result is None
                    or path_result.distance < 2
                ):
                    continue

                path = list(
                    path_result.path
                )

                if len(path) > 5:
                    continue

                relation_ids = self._path_edges(
                    relationships,
                    path,
                )

                generated.append(
                    IntelligenceFinding(
                        title="Indirect relationship path detected",
                        description=(
                            f"Entities {source_id} and {target_id} are "
                            f"indirectly connected through the relationship "
                            f"path {' → '.join(map(str, path))}. This "
                            f"indicates graph connectivity without asserting "
                            f"a direct relationship."
                        ),
                        severity=(
                            IntelligenceSeverity.HIGH
                            if len(path) - 2 >= 3
                            else IntelligenceSeverity.MEDIUM
                        ),
                        confidence=round(
                            min(
                                0.60
                                + 0.05 * (len(path) - 2),
                                0.85,
                            ),
                            3,
                        ),
                        supporting_entity_ids=path,
                        supporting_evidence_ids=[],
                        supporting_relationship_ids=relation_ids,
                    )
                )

        return generated

    # ========================================================
    # 9. CENTRAL + REINFORCED
    # ========================================================

    def _reason_central_reinforcement(
        self,
        *,
        findings: list[IntelligenceFinding],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        generated: list[IntelligenceFinding] = []

        for entity_id in self._safe_int_list(
            graph_analysis.central_entities
        ):

            high_count = sum(
                1
                for finding in findings
                if (
                    entity_id
                    in self._finding_entities(finding)
                    and finding.confidence
                    >= self.HIGH_CONFIDENCE
                )
            )

            if high_count < 2:
                continue

            related_entities: set[int] = set()
            relation_ids: set[int] = set()

            for finding in findings:

                if entity_id not in self._finding_entities(
                    finding
                ):
                    continue

                related_entities.update(
                    self._finding_entities(
                        finding
                    )
                )

                relation_ids.update(
                    self._safe_int_list(
                        finding.supporting_relationship_ids
                    )
                )

            confidence = min(
                0.76
                + high_count * 0.05,
                0.94,
            )

            generated.append(
                IntelligenceFinding(
                    title="Central entity with reinforced indicators",
                    description=(
                        f"Entity {entity_id} is a central entity in "
                        f"the investigation graph and is associated "
                        f"with {high_count} high-confidence intelligence "
                        f"finding(s). The combination of central graph "
                        f"position and multiple high-confidence indicators "
                        f"suggests reinforced investigative significance."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if high_count >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=sorted(
                        related_entities
                    ),
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=sorted(
                        relation_ids
                    ),
                )
            )

        return generated

    # ========================================================
    # 10. COMPOUND GRAPH PATTERN
    # ========================================================

    def _reason_compound_graph_pattern(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        if (
            not graph_analysis.central_entities
            or graph_analysis.node_count < 3
        ):
            return []

        generated: list[IntelligenceFinding] = []

        central_entities = self._safe_int_list(
            graph_analysis.central_entities
        )

        for entity_id in central_entities:

            high_count = sum(
                1
                for finding in findings
                if (
                    entity_id
                    in self._finding_entities(finding)
                    and finding.confidence
                    >= self.HIGH_CONFIDENCE
                )
            )

            entity_relationships: list[Any] = []

            for relationship in relationships:

                source_id, target_id = self._relationship_endpoints(
                    relationship
                )

                if (
                    source_id == entity_id
                    or target_id == entity_id
                ):
                    entity_relationships.append(
                        relationship
                    )

            relationship_count = len(
                entity_relationships
            )

            component: list[int] = []

            for raw_component in (
                graph_analysis.connected_components
                or []
            ):
                normalized = self._safe_int_list(
                    raw_component
                )

                if entity_id in normalized:
                    component = normalized
                    break

            component_size = len(
                component
            )

            if (
                high_count < 2
                or relationship_count < 2
                or component_size < 3
            ):
                continue

            confidence = min(
                0.76
                + high_count * 0.03
                + relationship_count * 0.02
                + component_size * 0.01,
                0.95,
            )

            relation_ids = [
                relationship_id
                for relationship in entity_relationships
                if (
                    relationship_id
                    := self._relationship_id(
                        relationship
                    )
                ) is not None
            ]

            generated.append(
                IntelligenceFinding(
                    title="Compound graph intelligence pattern",
                    description=(
                        f"Entity {entity_id} demonstrates a compound "
                        f"intelligence pattern: it is graph-central, "
                        f"appears in {high_count} high-confidence finding(s), "
                        f"participates in {relationship_count} relationship "
                        f"record(s), and belongs to a connected component "
                        f"containing {component_size} entities. These "
                        f"independent graph and intelligence signals "
                        f"reinforce the entity's investigative significance."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if confidence >= 0.90
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=component,
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 11. HUB AND SPOKE
    # ========================================================

    def _reason_hub_and_spoke(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        if not graph_analysis.central_entities:
            return []

        adjacency = self._build_adjacency(
            relationships
        )

        generated: list[IntelligenceFinding] = []

        for entity_id in self._safe_int_list(
            graph_analysis.central_entities
        ):

            neighbors = adjacency.get(
                entity_id,
                set(),
            )

            degree = len(
                neighbors
            )

            if degree < 3:
                continue

            relation_ids: list[int] = []

            for neighbor in neighbors:

                relation_ids.extend(
                    self._edge_ids_between(
                        relationships,
                        entity_id,
                        neighbor,
                    )
                )

            generated.append(
                IntelligenceFinding(
                    title="Hub-and-spoke graph pattern",
                    description=(
                        f"Entity {entity_id} functions as a hub connecting "
                        f"{degree} other investigation entities. This "
                        f"hub-and-spoke structure indicates concentrated "
                        f"network activity around the entity."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if degree >= 5
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.72
                            + degree * 0.04,
                            0.93,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id,
                        *sorted(neighbors),
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 12. BRIDGE ENTITIES
    # ========================================================

    def _reason_bridge_entities(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        # A node cannot literally connect two existing connected
        # components of the same graph: if it did, they would be
        # one component.
        #
        # Therefore bridge-like entities are detected using
        # articulation-point analysis.

        return self._reason_articulation_points(
            relationships=relationships,
            graph_analysis=graph_analysis,
        )

    # ========================================================
    # 13. REINFORCED MULTI-HOP PATHS
    # ========================================================

    def _reason_reinforced_multi_hop_paths(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if len(relationships) < 2:
            return []

        graph = IntelligenceGraph()

        graph.build(
            relationships=relationships
        )

        generated: list[IntelligenceFinding] = []

        entity_ids = sorted(
            graph.nodes.keys()
        )

        for index, source_id in enumerate(
            entity_ids
        ):
            for target_id in entity_ids[
                index + 1:
            ]:

                path_result = graph.find_path(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                )

                if (
                    path_result is None
                    or path_result.distance < 2
                ):
                    continue

                path = list(
                    path_result.path
                )

                if len(path) > 5:
                    continue

                path_entities = set(
                    path
                )

                supporting_relationship_ids = set(
                    self._path_edges(
                        relationships,
                        path,
                    )
                )

                high_confidence_count = 0

                for finding in findings:

                    if not path_entities.intersection(
                        self._finding_entities(
                            finding
                        )
                    ):
                        continue

                    if finding.confidence >= self.HIGH_CONFIDENCE:
                        high_confidence_count += 1

                    supporting_relationship_ids.update(
                        self._safe_int_list(
                            finding.supporting_relationship_ids
                        )
                    )

                if high_confidence_count < 1:
                    continue

                confidence = min(
                    0.68
                    + path_result.distance * 0.04
                    + high_confidence_count * 0.04,
                    0.92,
                )

                generated.append(
                    IntelligenceFinding(
                        title="Reinforced multi-hop relationship path",
                        description=(
                            f"Entities {source_id} and {target_id} are "
                            f"connected through the multi-hop path "
                            f"{' → '.join(map(str, path))}, and the path "
                            f"is reinforced by {high_confidence_count} "
                            f"high-confidence intelligence indicator(s). "
                            f"This strengthens the significance of the "
                            f"observed graph connectivity without asserting "
                            f"an unobserved direct relationship."
                        ),
                        severity=(
                            IntelligenceSeverity.HIGH
                            if high_confidence_count >= 2
                            else IntelligenceSeverity.MEDIUM
                        ),
                        confidence=round(
                            confidence,
                            3,
                        ),
                        supporting_entity_ids=path,
                        supporting_evidence_ids=[],
                        supporting_relationship_ids=sorted(
                            supporting_relationship_ids
                        ),
                    )
                )

        return generated

    # ========================================================
    # 14. RELATIONSHIP TYPE CONVERGENCE
    # ========================================================

    def _reason_relationship_convergence(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        entity_types: dict[
            int,
            set[str],
        ] = defaultdict(set)

        entity_relation_ids: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for relationship in relationships:

            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_type = self._relationship_type(
                relationship
            )

            relationship_id = self._relationship_id(
                relationship
            )

            if relationship_type is None:
                continue

            for entity_id in (
                source_id,
                target_id,
            ):

                if entity_id is None:
                    continue

                entity_types[entity_id].add(
                    relationship_type
                )

                if relationship_id is not None:
                    entity_relation_ids[
                        entity_id
                    ].append(
                        relationship_id
                    )

        generated: list[IntelligenceFinding] = []

        for entity_id, types in entity_types.items():

            if len(types) < 2:
                continue

            generated.append(
                IntelligenceFinding(
                    title="Relationship type convergence",
                    description=(
                        f"Multiple relationship types converge on entity "
                        f"{entity_id}: {', '.join(sorted(types))}. This "
                        f"indicates that the entity occupies multiple "
                        f"relationship roles within the investigation network."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if len(types) >= 4
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.70 + len(types) * 0.05,
                            0.91,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            entity_relation_ids[
                                entity_id
                            ]
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 15. CENTRAL CLUSTER
    # ========================================================

    def _reason_central_cluster(
        self,
        *,
        findings: list[IntelligenceFinding],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        generated: list[IntelligenceFinding] = []

        central_entities = set(
            self._safe_int_list(
                graph_analysis.central_entities
            )
        )

        for raw_component in (
            graph_analysis.connected_components
            or []
        ):

            component = self._safe_int_list(
                raw_component
            )

            if len(component) < 3:
                continue

            component_set = set(
                component
            )

            central_in_component = sorted(
                central_entities.intersection(
                    component_set
                )
            )

            if not central_in_component:
                continue

            component_findings = [
                finding
                for finding in findings
                if (
                    self._finding_entities(
                        finding
                    ).intersection(
                        central_in_component
                    )
                    and self._finding_entities(
                        finding
                    ).intersection(
                        component_set
                    )
                )
            ]

            high_count = sum(
                1
                for finding in component_findings
                if finding.confidence
                >= self.HIGH_CONFIDENCE
            )

            generated.append(
                IntelligenceFinding(
                    title="Centralized intelligence cluster",
                    description=(
                        f"A connected investigation cluster contains "
                        f"{len(component)} entities and includes central "
                        f"entity {', '.join(map(str, central_in_component))}. "
                        f"The cluster also contains {high_count} "
                        f"high-confidence indicator(s), suggesting "
                        f"concentrated investigative activity within the "
                        f"connected network."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if high_count >= 3
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.72
                            + len(component) * 0.025
                            + high_count * 0.03,
                            0.94,
                        ),
                        3,
                    ),
                    supporting_entity_ids=component,
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=[],
                )
            )

        return generated

    # ========================================================
    # 16. RECIPROCAL RELATIONSHIPS
    # ========================================================

    def _reason_reciprocal_relationships(
        self,
        *,
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if not relationships:
            return []

        directions: dict[
            tuple[int, int],
            list[int],
        ] = defaultdict(list)

        for relationship in relationships:

            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_id = self._relationship_id(
                relationship
            )

            if (
                source_id is None
                or target_id is None
                or source_id == target_id
            ):
                continue

            if relationship_id is not None:
                directions[
                    (
                        source_id,
                        target_id,
                    )
                ].append(
                    relationship_id
                )

        generated: list[IntelligenceFinding] = []

        seen_pairs: set[
            tuple[int, int]
        ] = set()

        for (
            source_id,
            target_id,
        ), first_ids in directions.items():

            pair = tuple(
                sorted(
                    (
                        source_id,
                        target_id,
                    )
                )
            )

            if pair in seen_pairs:
                continue

            reverse_ids = directions.get(
                (
                    target_id,
                    source_id,
                ),
                [],
            )

            if not reverse_ids:
                continue

            seen_pairs.add(
                pair
            )

            relation_ids = list(
                dict.fromkeys(
                    first_ids
                    + reverse_ids
                )
            )

            generated.append(
                IntelligenceFinding(
                    title="Reciprocal relationship pattern",
                    description=(
                        f"Observed relationships exist in both directions "
                        f"between entities {source_id} and {target_id}. "
                        f"This reciprocal structure indicates bidirectional "
                        f"graph interaction without inferring intent."
                    ),
                    severity=IntelligenceSeverity.MEDIUM,
                    confidence=0.82,
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=relation_ids,
                )
            )

        return generated

    # ========================================================
    # 17. REPEATED RELATIONSHIPS
    # ========================================================

    def _reason_repeated_relationships(
        self,
        *,
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if not relationships:
            return []

        pair_type_ids: dict[
            tuple[
                tuple[int, int],
                str,
            ],
            list[int],
        ] = defaultdict(list)

        for relationship in relationships:

            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_type = self._relationship_type(
                relationship
            )

            relationship_id = self._relationship_id(
                relationship
            )

            if (
                source_id is None
                or target_id is None
                or relationship_type is None
            ):
                continue

            pair = tuple(
                sorted(
                    (
                        source_id,
                        target_id,
                    )
                )
            )

            if relationship_id is not None:
                pair_type_ids[
                    (
                        pair,
                        relationship_type,
                    )
                ].append(
                    relationship_id
                )

        generated: list[IntelligenceFinding] = []

        for (
            (
                pair,
                relationship_type,
            ),
            relation_ids,
        ) in pair_type_ids.items():

            if len(relation_ids) < 2:
                continue

            source_id, target_id = pair

            generated.append(
                IntelligenceFinding(
                    title="Repeated relationship pattern",
                    description=(
                        f"Entities {source_id} and {target_id} have "
                        f"{len(relation_ids)} recorded relationship(s) "
                        f"of type '{relationship_type}'. Repetition of "
                        f"the same relationship type is a stronger "
                        f"structural signal than a single edge."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if len(relation_ids) >= 4
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.72
                            + len(relation_ids) * 0.04,
                            0.92,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 18. TRIANGLE / CLOSED-MOTIF DETECTION
    # ========================================================

    def _reason_triangles(
        self,
        *,
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        adjacency = self._build_adjacency(
            relationships
        )

        if len(adjacency) < 3:
            return []

        triangles: list[
            tuple[int, int, int]
        ] = []

        nodes = sorted(
            adjacency
        )

        for i, a in enumerate(nodes):

            for b in sorted(
                n
                for n in adjacency[a]
                if n > a
            ):

                common = adjacency[a].intersection(
                    adjacency.get(
                        b,
                        set(),
                    )
                )

                for c in sorted(
                    n
                    for n in common
                    if n > b
                ):
                    triangles.append(
                        (
                            a,
                            b,
                            c,
                        )
                    )

        generated: list[IntelligenceFinding] = []

        for a, b, c in triangles:

            relation_ids: list[int] = []

            relation_ids.extend(
                self._edge_ids_between(
                    relationships,
                    a,
                    b,
                )
            )

            relation_ids.extend(
                self._edge_ids_between(
                    relationships,
                    b,
                    c,
                )
            )

            relation_ids.extend(
                self._edge_ids_between(
                    relationships,
                    a,
                    c,
                )
            )

            generated.append(
                IntelligenceFinding(
                    title="Closed triadic graph pattern",
                    description=(
                        f"Entities {a}, {b}, and {c} form a closed "
                        f"three-entity relationship motif: each entity "
                        f"is directly connected to the other two. This "
                        f"indicates a more densely interconnected local "
                        f"network than a simple chain."
                    ),
                    severity=IntelligenceSeverity.MEDIUM,
                    confidence=0.84,
                    supporting_entity_ids=[
                        a,
                        b,
                        c,
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 19. ARTICULATION / TRUE BRIDGE POINTS
    # ========================================================

    def _reason_articulation_points(
        self,
        *,
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        adjacency = self._build_adjacency(
            relationships
        )

        if len(adjacency) < 3:
            return []

        # Tarjan articulation-point algorithm.
        discovery: dict[int, int] = {}
        low: dict[int, int] = {}
        parent: dict[
            int,
            int | None,
        ] = {}

        articulation: set[int] = set()

        time = 0

        def dfs(node: int) -> None:
            nonlocal time

            time += 1

            discovery[node] = time
            low[node] = time

            children = 0

            for neighbor in adjacency.get(
                node,
                set(),
            ):

                if neighbor not in discovery:

                    parent[neighbor] = node
                    children += 1

                    dfs(
                        neighbor
                    )

                    low[node] = min(
                        low[node],
                        low[neighbor],
                    )

                    # Root articulation condition.
                    if (
                        parent.get(node) is None
                        and children > 1
                    ):
                        articulation.add(
                            node
                        )

                    # Non-root articulation condition.
                    if (
                        parent.get(node) is not None
                        and low[neighbor]
                        >= discovery[node]
                    ):
                        articulation.add(
                            node
                        )

                elif neighbor != parent.get(
                    node
                ):
                    low[node] = min(
                        low[node],
                        discovery[neighbor],
                    )

        for node in sorted(
            adjacency
        ):

            if node not in discovery:

                parent[node] = None

                dfs(
                    node
                )

        generated: list[IntelligenceFinding] = []

        for entity_id in sorted(
            articulation
        ):

            neighbors = sorted(
                adjacency.get(
                    entity_id,
                    set(),
                )
            )

            if len(neighbors) < 2:
                continue

            relation_ids: list[int] = []

            for neighbor in neighbors:

                relation_ids.extend(
                    self._edge_ids_between(
                        relationships,
                        entity_id,
                        neighbor,
                    )
                )

            generated.append(
                IntelligenceFinding(
                    title="Bridge / articulation entity detected",
                    description=(
                        f"Entity {entity_id} is an articulation point in "
                        f"the investigation graph: removing it would "
                        f"separate at least one portion of its local "
                        f"network. This indicates structural bridge "
                        f"importance without asserting causation or intent."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if len(neighbors) >= 4
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        min(
                            0.78
                            + len(neighbors) * 0.03,
                            0.93,
                        ),
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id,
                        *neighbors,
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # 20. TYPED PATH REINFORCEMENT
    # ========================================================

    def _reason_typed_path_reinforcement(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:

        if len(relationships) < 2:
            return []

        adjacency = self._build_adjacency(
            relationships
        )

        if len(adjacency) < 3:
            return []

        pair_types: dict[
            tuple[int, int],
            set[str],
        ] = defaultdict(set)

        for relationship in relationships:

            source_id, target_id = self._relationship_endpoints(
                relationship
            )

            relationship_type = self._relationship_type(
                relationship
            )

            if (
                source_id is None
                or target_id is None
                or relationship_type is None
            ):
                continue

            pair_types[
                tuple(
                    sorted(
                        (
                            source_id,
                            target_id,
                        )
                    )
                )
            ].add(
                relationship_type
            )

        generated: list[IntelligenceFinding] = []

        seen: set[
            tuple[
                int,
                int,
                int,
                tuple[str, ...],
            ]
        ] = set()

        for middle in sorted(
            adjacency
        ):

            neighbors = sorted(
                adjacency[middle]
            )

            for i, left in enumerate(
                neighbors
            ):

                for right in neighbors[
                    i + 1:
                ]:

                    left_types = pair_types.get(
                        tuple(
                            sorted(
                                (
                                    left,
                                    middle,
                                )
                            )
                        ),
                        set(),
                    )

                    right_types = pair_types.get(
                        tuple(
                            sorted(
                                (
                                    middle,
                                    right,
                                )
                            )
                        ),
                        set(),
                    )

                    if (
                        not left_types
                        or not right_types
                    ):
                        continue

                    combinations = {
                        (
                            left_type,
                            right_type,
                        )
                        for left_type in left_types
                        for right_type in right_types
                        if left_type != right_type
                    }

                    if not combinations:
                        continue

                    type_text = tuple(
                        sorted(
                            {
                                f"{left_type}→{right_type}"
                                for left_type, right_type
                                in combinations
                            }
                        )
                    )

                    key = (
                        left,
                        middle,
                        right,
                        type_text,
                    )

                    if key in seen:
                        continue

                    seen.add(
                        key
                    )

                    relation_ids: list[int] = []

                    relation_ids.extend(
                        self._edge_ids_between(
                            relationships,
                            left,
                            middle,
                        )
                    )

                    relation_ids.extend(
                        self._edge_ids_between(
                            relationships,
                            middle,
                            right,
                        )
                    )

                    generated.append(
                        IntelligenceFinding(
                            title="Typed multi-hop graph pattern",
                            description=(
                                f"Entities {left} and {right} are connected "
                                f"through intermediary entity {middle} by "
                                f"different observed relationship types "
                                f"({', '.join(type_text)}). This identifies "
                                f"a typed multi-hop structure without "
                                f"asserting an unobserved direct relationship."
                            ),
                            severity=IntelligenceSeverity.MEDIUM,
                            confidence=0.83,
                            supporting_entity_ids=[
                                left,
                                middle,
                                right,
                            ],
                            supporting_evidence_ids=[],
                            supporting_relationship_ids=list(
                                dict.fromkeys(
                                    relation_ids
                                )
                            ),
                        )
                    )

        return generated

    # ========================================================
    # 21. INDEPENDENT SIGNAL CONVERGENCE
    # ========================================================

    def _reason_independent_signal_convergence(
        self,
        *,
        findings: list[IntelligenceFinding],
        relationships: list[Any],
        graph_analysis: IntelligenceGraphAnalysis,
    ) -> list[IntelligenceFinding]:

        if not graph_analysis.central_entities:
            return []

        generated: list[IntelligenceFinding] = []

        adjacency = self._build_adjacency(
            relationships
        )

        for entity_id in self._safe_int_list(
            graph_analysis.central_entities
        ):

            neighbors = adjacency.get(
                entity_id,
                set(),
            )

            degree = len(
                neighbors
            )

            if degree < 2:
                continue

            high_conf = [
                finding
                for finding in findings
                if (
                    entity_id
                    in self._finding_entities(
                        finding
                    )
                    and finding.confidence
                    >= self.HIGH_CONFIDENCE
                )
            ]

            finding_titles = {
                finding.title
                for finding in high_conf
            }

            relationship_types: set[str] = set()
            relation_ids: list[int] = []

            for relationship in relationships:

                source_id, target_id = self._relationship_endpoints(
                    relationship
                )

                if (
                    source_id != entity_id
                    and target_id != entity_id
                ):
                    continue

                relationship_type = self._relationship_type(
                    relationship
                )

                relationship_id = self._relationship_id(
                    relationship
                )

                if relationship_type is not None:
                    relationship_types.add(
                        relationship_type
                    )

                if relationship_id is not None:
                    relation_ids.append(
                        relationship_id
                    )

            # Require genuinely different signal families.
            signal_count = 0

            if degree >= 2:
                signal_count += 1

            if len(high_conf) >= 2:
                signal_count += 1

            if len(relationship_types) >= 2:
                signal_count += 1

            if len(finding_titles) >= 2:
                signal_count += 1

            if signal_count < 3:
                continue

            confidence = min(
                0.80
                + signal_count * 0.025
                + len(relationship_types) * 0.01,
                0.96,
            )

            generated.append(
                IntelligenceFinding(
                    title="Independent intelligence signal convergence",
                    description=(
                        f"Entity {entity_id} exhibits convergence across "
                        f"{signal_count} independent signal categories: "
                        f"graph connectivity, high-confidence intelligence "
                        f"indicators, relationship-type diversity, and/or "
                        f"distinct finding families. Multiple independent "
                        f"signals reinforce the entity's structural "
                        f"significance in the investigation."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if signal_count >= 4
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id,
                        *sorted(neighbors),
                    ],
                    supporting_evidence_ids=[],
                    supporting_relationship_ids=list(
                        dict.fromkeys(
                            relation_ids
                        )
                    ),
                )
            )

        return generated

    # ========================================================
    # DUPLICATE REMOVAL
    # ========================================================

    def _remove_duplicates(
        self,
        findings: list[IntelligenceFinding],
    ) -> list[IntelligenceFinding]:

        seen: set[
            tuple[
                str,
                tuple[int, ...],
                tuple[int, ...],
                tuple[int, ...],
            ]
        ] = set()

        unique: list[IntelligenceFinding] = []

        for finding in findings:

            key = (
                finding.title,
                tuple(
                    sorted(
                        self._safe_int_list(
                            finding.supporting_entity_ids
                        )
                    )
                ),
                tuple(
                    sorted(
                        self._safe_int_list(
                            finding.supporting_evidence_ids
                        )
                    )
                ),
                tuple(
                    sorted(
                        self._safe_int_list(
                            finding.supporting_relationship_ids
                        )
                    )
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            unique.append(
                finding
            )

        return unique

    # ========================================================
    # SAFE INTEGER HELPERS
    # ========================================================

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> int | None:

        if value is None:
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @classmethod
    def _safe_int_list(
        cls,
        values: Any,
    ) -> list[int]:

        if values is None:
            return []

        result: list[int] = []

        try:
            iterator = iter(
                values
            )
        except TypeError:
            iterator = iter(
                [values]
            )

        for value in iterator:

            converted = cls._safe_int(
                value
            )

            if converted is not None:
                result.append(
                    converted
                )

        return result


# ============================================================
# DEFAULT REASONER
# ============================================================

intelligence_reasoner = IntelligenceReasoner()
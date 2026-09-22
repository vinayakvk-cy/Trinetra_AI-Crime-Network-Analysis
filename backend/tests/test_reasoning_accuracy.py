from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch
from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceSeverity,
)
from app.ai.intelligence.reasoning import IntelligenceReasoner


# ============================================================
# TEST FIXTURES
# ============================================================


@dataclass
class RelationshipFixture:
    id: int | None
    source_entity_id: int | None
    target_entity_id: int | None
    relationship_type: str | None
    confidence: float = 0.90


@dataclass
class EntityFixture:
    id: int
    name: str = "Entity"


@pytest.fixture
def reasoner() -> IntelligenceReasoner:
    return IntelligenceReasoner()


def make_entity(entity_id: int, name: str | None = None) -> EntityFixture:
    return EntityFixture(
        id=entity_id,
        name=name or f"Entity-{entity_id}",
    )


def make_relationship(
    relationship_id: int | None,
    source_id: int | None,
    target_id: int | None,
    relationship_type: str | None,
    confidence: float = 0.90,
) -> RelationshipFixture:
    return RelationshipFixture(
        id=relationship_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=relationship_type,
        confidence=confidence,
    )


def make_finding(
    *,
    title: str = "Test finding",
    confidence: float = 0.90,
    entities: list[int] | None = None,
    evidence: list[int] | None = None,
    relationships: list[int] | None = None,
    severity: IntelligenceSeverity = IntelligenceSeverity.MEDIUM,
) -> IntelligenceFinding:
    return IntelligenceFinding(
        title=title,
        description="Test intelligence finding.",
        severity=severity,
        confidence=confidence,
        supporting_entity_ids=entities or [],
        supporting_evidence_ids=evidence or [],
        supporting_relationship_ids=relationships or [],
    )


def make_graph_analysis(
    *,
    central_entities: list[int] | None = None,
    connected_components: list[list[int]] | None = None,
    node_count: int = 0,
    edge_count: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        central_entities=central_entities or [],
        connected_components=connected_components or [],
        node_count=node_count,
        edge_count=edge_count,
    )


# ============================================================
# BASIC HELPERS
# ============================================================


def test_relationship_type_none_returns_none(
    reasoner: IntelligenceReasoner,
) -> None:
    relationship = make_relationship(
        1,
        1,
        2,
        None,
    )

    assert reasoner._relationship_type(relationship) is None


def test_relationship_type_plain_value(
    reasoner: IntelligenceReasoner,
) -> None:
    relationship = make_relationship(
        1,
        1,
        2,
        "contacted",
    )

    assert reasoner._relationship_type(relationship) == "contacted"


def test_relationship_type_enum_like_object(
    reasoner: IntelligenceReasoner,
) -> None:
    relationship = SimpleNamespace(
        relationship_type=SimpleNamespace(value="contacted")
    )

    assert reasoner._relationship_type(relationship) == "contacted"


def test_relationship_id_missing_returns_none(
    reasoner: IntelligenceReasoner,
) -> None:
    relationship = SimpleNamespace(
        source_entity_id=1,
        target_entity_id=2,
        relationship_type="contacted",
    )

    assert reasoner._relationship_id(relationship) is None


# ============================================================
# ADJACENCY
# ============================================================


def test_build_adjacency_ignores_missing_source(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            None,
            2,
            "contacted",
        )
    ]

    assert reasoner._build_adjacency(relationships) == {}


def test_build_adjacency_ignores_missing_target(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            None,
            "contacted",
        )
    ]

    assert reasoner._build_adjacency(relationships) == {}


def test_build_adjacency_handles_self_loop(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            1,
            "contacted",
        )
    ]

    result = reasoner._build_adjacency(relationships)

    assert result == {1: {1}}


def test_build_adjacency_is_undirected(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            2,
            "contacted",
        )
    ]

    result = reasoner._build_adjacency(relationships)

    assert result[1] == {2}
    assert result[2] == {1}


def test_neighbors_returns_neighbors(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    assert reasoner._neighbors(
        relationships,
        1,
    ) == {2, 3}


def test_neighbors_unknown_entity_returns_empty(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
    ]

    assert reasoner._neighbors(
        relationships,
        99,
    ) == set()


# ============================================================
# ENTITY ACTIVITY
# ============================================================


def test_entity_activity_empty_relationships(
    reasoner: IntelligenceReasoner,
) -> None:
    result = reasoner._reason_entity_activity(
        findings=[],
        entities=[],
        relationships=[],
    )

    assert result == []


def test_entity_activity_detects_concentration(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    result = reasoner._reason_entity_activity(
        findings=[],
        entities=[
            make_entity(1),
            make_entity(2),
            make_entity(3),
        ],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Entity activity concentration"
    ]

    assert matching
    assert matching[0].confidence == 0.70
    assert matching[0].supporting_entity_ids == [1, 2, 3]


# ============================================================
# RELATIONSHIP PATTERNS
# ============================================================


def test_relationship_patterns_empty(
    reasoner: IntelligenceReasoner,
) -> None:
    result = reasoner._reason_relationship_patterns(
        findings=[],
        relationships=[],
    )

    assert result == []


def test_relationship_patterns_ignore_none_type(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, None),
        make_relationship(2, 1, 2, "contacted"),
    ]

    result = reasoner._reason_relationship_patterns(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_relationship_patterns_require_valid_endpoints(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, None, 2, "contacted"),
        make_relationship(2, 1, None, "uses"),
    ]

    result = reasoner._reason_relationship_patterns(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_relationship_patterns_detect_multiple_types(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 2, "uses"),
    ]

    result = reasoner._reason_relationship_patterns(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Multiple relationship indicators"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2]
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


# ============================================================
# EVIDENCE REINFORCEMENT
# ============================================================


def test_evidence_reinforcement_ignores_unknown_evidence(
    reasoner: IntelligenceReasoner,
) -> None:
    findings = [
        make_finding(
            title="Finding A",
            entities=[1],
            evidence=[999],
        ),
        make_finding(
            title="Finding B",
            entities=[1],
            evidence=[999],
        ),
    ]

    evidence = [
        SimpleNamespace(id=1)
    ]

    result = reasoner._reason_evidence_reinforcement(
        findings=findings,
        evidence=evidence,
    )

    assert result == []


def test_evidence_reinforcement_requires_two_findings(
    reasoner: IntelligenceReasoner,
) -> None:
    findings = [
        make_finding(
            title="Finding A",
            entities=[1],
            evidence=[1],
        )
    ]

    evidence = [
        SimpleNamespace(id=1)
    ]

    result = reasoner._reason_evidence_reinforcement(
        findings=findings,
        evidence=evidence,
    )

    assert result == []


def test_evidence_reinforcement_generates_finding(
    reasoner: IntelligenceReasoner,
) -> None:
    findings = [
        make_finding(
            title="Finding A",
            entities=[1],
            evidence=[1],
            relationships=[10],
        ),
        make_finding(
            title="Finding B",
            entities=[2],
            evidence=[1],
            relationships=[11],
        ),
    ]

    evidence = [
        SimpleNamespace(id=1)
    ]

    result = reasoner._reason_evidence_reinforcement(
        findings=findings,
        evidence=evidence,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Evidence reinforcement detected"
    ]

    assert matching
    assert matching[0].supporting_evidence_ids == [1]
    assert set(matching[0].supporting_entity_ids) == {1, 2}
    assert set(matching[0].supporting_relationship_ids) == {10, 11}


# ============================================================
# INDIRECT RELATIONSHIPS
# ============================================================


def test_indirect_relationships_ignore_direct_paths(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
    ]

    result = reasoner._reason_indirect_relationships(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_indirect_relationships_detect_two_hop_path(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    result = reasoner._reason_indirect_relationships(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Indirect relationship path detected"
    ]

    assert matching

    assert any(
        finding.supporting_entity_ids == [1, 2, 3]
        for finding in matching
    )


def test_indirect_relationship_skips_long_path(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
        make_relationship(3, 3, 4, "owns"),
        make_relationship(4, 4, 5, "visited"),
        make_relationship(5, 5, 6, "knows"),
        make_relationship(6, 6, 7, "knows"),
    ]

    result = reasoner._reason_indirect_relationships(
        findings=[],
        relationships=relationships,
    )

    assert not any(
        finding.supporting_entity_ids == [1, 2, 3, 4, 5, 6, 7]
        for finding in result
    )


# ============================================================
# CENTRAL REINFORCEMENT
# ============================================================


def test_central_reinforcement_requires_two_high_confidence_findings(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[1]
    )

    findings = [
        make_finding(
            title="High A",
            confidence=0.95,
            entities=[1],
        )
    ]

    result = reasoner._reason_central_reinforcement(
        findings=findings,
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_central_reinforcement_generates_finding(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[1]
    )

    findings = [
        make_finding(
            title="High A",
            confidence=0.90,
            entities=[1, 2],
            relationships=[10],
        ),
        make_finding(
            title="High B",
            confidence=0.95,
            entities=[1, 3],
            relationships=[11],
        ),
    ]

    result = reasoner._reason_central_reinforcement(
        findings=findings,
        graph_analysis=graph_analysis,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Central entity with reinforced indicators"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]
    assert set(matching[0].supporting_relationship_ids) == {10, 11}


# ============================================================
# COMPOUND GRAPH PATTERN
# ============================================================


def test_compound_graph_pattern_requires_component_and_relationships(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[1],
        connected_components=[[1, 2]],
        node_count=2,
        edge_count=1,
    )

    result = reasoner._reason_compound_graph_pattern(
        findings=[],
        relationships=[],
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_compound_graph_pattern_requires_enough_high_confidence_findings(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[1],
        connected_components=[[1, 2, 3]],
        node_count=3,
        edge_count=2,
    )

    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    findings = [
        make_finding(
            title="Only one high-confidence finding",
            confidence=0.95,
            entities=[1],
        )
    ]

    result = reasoner._reason_compound_graph_pattern(
        findings=findings,
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_compound_graph_pattern_generates_when_all_conditions_hold(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[1],
        connected_components=[[1, 2, 3]],
        node_count=3,
        edge_count=2,
    )

    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    findings = [
        make_finding(
            title="High A",
            confidence=0.95,
            entities=[1],
        ),
        make_finding(
            title="High B",
            confidence=0.95,
            entities=[1],
        ),
    ]

    result = reasoner._reason_compound_graph_pattern(
        findings=findings,
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Compound graph intelligence pattern"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


# ============================================================
# BRIDGE / ARTICULATION
# ============================================================


def test_bridge_entities_delegates_to_articulation(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    graph_analysis = make_graph_analysis(
        node_count=3,
        edge_count=2,
    )

    result = reasoner._reason_bridge_entities(
        findings=[],
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    assert any(
        finding.title == "Bridge / articulation entity detected"
        for finding in result
    )


def test_articulation_skips_entity_with_less_than_two_neighbors(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
    ]

    graph_analysis = make_graph_analysis(
        node_count=2,
        edge_count=1,
    )

    result = reasoner._reason_articulation_points(
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_articulation_detects_middle_entity(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    graph_analysis = make_graph_analysis(
        node_count=3,
        edge_count=2,
    )

    result = reasoner._reason_articulation_points(
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Bridge / articulation entity detected"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [2, 1, 3]


# ============================================================
# REINFORCED MULTI-HOP PATHS
# ============================================================


def test_reinforced_multi_hop_paths_requires_two_relationships(
    reasoner: IntelligenceReasoner,
) -> None:
    result = reasoner._reason_reinforced_multi_hop_paths(
        findings=[],
        relationships=[
            make_relationship(1, 1, 2, "contacted")
        ],
    )

    assert result == []


def test_reinforced_multihop_skips_long_paths(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
        make_relationship(3, 3, 4, "owns"),
        make_relationship(4, 4, 5, "visited"),
        make_relationship(5, 5, 6, "knows"),
        make_relationship(6, 6, 7, "knows"),
    ]

    findings = [
        make_finding(
            title="High-confidence indicator",
            confidence=0.95,
            entities=[2],
            relationships=[1],
        )
    ]

    result = reasoner._reason_reinforced_multi_hop_paths(
        findings=findings,
        relationships=relationships,
    )

    assert not any(
        finding.supporting_entity_ids == [1, 2, 3, 4, 5, 6, 7]
        for finding in result
    )


def test_reinforced_multihop_requires_high_confidence(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    findings = [
        make_finding(
            title="Low-confidence indicator",
            confidence=0.30,
            entities=[2],
            relationships=[1],
        )
    ]

    result = reasoner._reason_reinforced_multi_hop_paths(
        findings=findings,
        relationships=relationships,
    )

    assert result == []


def test_reinforced_multihop_generates_with_high_confidence(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    findings = [
        make_finding(
            title="High-confidence indicator",
            confidence=0.95,
            entities=[2],
            relationships=[1],
        )
    ]

    result = reasoner._reason_reinforced_multi_hop_paths(
        findings=findings,
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Reinforced multi-hop relationship path"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


# ============================================================
# RELATIONSHIP TYPE CONVERGENCE
# ============================================================


def test_relationship_convergence_ignores_none_type(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            2,
            None,
        )
    ]

    result = reasoner._reason_relationship_convergence(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_relationship_convergence_ignores_missing_entity(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            None,
            2,
            "contacted",
        ),
        make_relationship(
            2,
            None,
            2,
            "uses",
        ),
    ]

    result = reasoner._reason_relationship_convergence(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Relationship type convergence"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [2]


def test_relationship_convergence_generates_for_multiple_types(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    result = reasoner._reason_relationship_convergence(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Relationship type convergence"
    ]

    assert matching
    entity_one = next(
        finding
        for finding in matching
        if finding.supporting_entity_ids == [1]
    )

    assert set(entity_one.supporting_relationship_ids) == {1, 2}


# ============================================================
# CENTRAL CLUSTER
# ============================================================


def test_central_cluster_skips_component_without_central(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        connected_components=[[1, 2, 3]],
        central_entities=[],
    )

    result = reasoner._reason_central_cluster(
        findings=[],
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_central_cluster_generates_for_central_component(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        connected_components=[[1, 2, 3]],
        central_entities=[1],
    )

    findings = [
        make_finding(
            title="High indicator A",
            confidence=0.95,
            entities=[1, 2],
        ),
        make_finding(
            title="High indicator B",
            confidence=0.90,
            entities=[1, 3],
        ),
    ]

    result = reasoner._reason_central_cluster(
        findings=findings,
        graph_analysis=graph_analysis,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Centralized intelligence cluster"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]


# ============================================================
# RECIPROCAL RELATIONSHIPS
# ============================================================


def test_reciprocal_relationships_empty(
    reasoner: IntelligenceReasoner,
) -> None:
    result = reasoner._reason_reciprocal_relationships(
        relationships=[]
    )

    assert result == []


def test_reciprocal_relationships_require_valid_endpoints(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, None, 2, "contacted"),
        make_relationship(2, 2, None, "contacted"),
    ]

    result = reasoner._reason_reciprocal_relationships(
        relationships=relationships
    )

    assert result == []


def test_reciprocal_relationships_detect_reverse_edges(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 1, "contacted"),
    ]

    result = reasoner._reason_reciprocal_relationships(
        relationships=relationships
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Reciprocal relationship pattern"
    ]

    assert matching
    assert set(matching[0].supporting_entity_ids) == {1, 2}
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


# ============================================================
# REPEATED RELATIONSHIPS
# ============================================================


def test_repeated_relationships_empty(
    reasoner: IntelligenceReasoner,
) -> None:
    result = reasoner._reason_repeated_relationships(
        relationships=[]
    )

    assert result == []


def test_repeated_relationships_ignore_none_type(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, None),
        make_relationship(2, 1, 2, "contacted"),
    ]

    result = reasoner._reason_repeated_relationships(
        relationships=relationships
    )

    assert result == []


def test_repeated_relationships_detect_repetition(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 2, "contacted"),
    ]

    result = reasoner._reason_repeated_relationships(
        relationships=relationships
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Repeated relationship pattern"
    ]

    assert matching
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


# ============================================================
# TYPED PATH REINFORCEMENT
# ============================================================


def test_typed_path_ignores_missing_type(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, None),
        make_relationship(2, 2, 3, "uses"),
    ]

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_typed_path_requires_types_on_both_edges(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, None),
    ]

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_typed_path_detects_different_relationship_types(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
    ]

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Typed multi-hop graph pattern"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]
    assert set(matching[0].supporting_relationship_ids) == {1, 2}
    assert "contacted→uses" in matching[0].description


def test_typed_path_same_type_does_not_create_pattern(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "contacted"),
    ]

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    assert result == []


def test_typed_path_duplicate_combinations_removed(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
        make_relationship(3, 1, 2, "contacted"),
        make_relationship(4, 2, 3, "uses"),
    ]

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Typed multi-hop graph pattern"
    ]

    assert len(matching) == 1
    assert set(matching[0].supporting_relationship_ids) == {
        1,
        2,
        3,
        4,
    }


# ============================================================
# INDEPENDENT SIGNAL CONVERGENCE
# ============================================================


def test_independent_signal_convergence_requires_central_entity(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis(
        central_entities=[]
    )

    result = reasoner._reason_independent_signal_convergence(
        findings=[],
        relationships=[],
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_independent_signal_convergence_requires_multiple_signals(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "contacted"),
    ]

    graph_analysis = make_graph_analysis(
        central_entities=[1]
    )

    findings = [
        make_finding(
            title="Only one indicator",
            confidence=0.95,
            entities=[1],
        )
    ]

    result = reasoner._reason_independent_signal_convergence(
        findings=findings,
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_independent_signal_convergence_detects_multiple_signal_families(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 1, 3, "uses"),
    ]

    graph_analysis = make_graph_analysis(
        central_entities=[1]
    )

    findings = [
        make_finding(
            title="High indicator A",
            confidence=0.95,
            entities=[1],
        ),
        make_finding(
            title="High indicator B",
            confidence=0.92,
            entities=[1],
        ),
    ]

    result = reasoner._reason_independent_signal_convergence(
        findings=findings,
        relationships=relationships,
        graph_analysis=graph_analysis,
    )

    matching = [
        finding
        for finding in result
        if finding.title == "Independent intelligence signal convergence"
    ]

    assert matching
    assert matching[0].supporting_entity_ids == [1, 2, 3]


# ============================================================
# SAFE INTEGER HELPERS
# ============================================================


def test_safe_int_list_none(
    reasoner: IntelligenceReasoner,
) -> None:
    assert reasoner._safe_int_list(None) == []


def test_safe_int_list_scalar(
    reasoner: IntelligenceReasoner,
) -> None:
    assert reasoner._safe_int_list(12) == [12]


def test_safe_int_list_string_scalar(
    reasoner: IntelligenceReasoner,
) -> None:
    # The implementation treats strings as iterables, so "12"
    # becomes two scalar values rather than integer 12.
    assert reasoner._safe_int_list("12") == [1, 2]


def test_safe_int_list_mixed_values(
    reasoner: IntelligenceReasoner,
) -> None:
    values = [
        1,
        "2",
        "invalid",
        None,
        3.9,
    ]

    result = reasoner._safe_int_list(values)

    assert result == [1, 2, 3]


def test_safe_int_list_empty_iterable(
    reasoner: IntelligenceReasoner,
) -> None:
    assert reasoner._safe_int_list([]) == []


# ============================================================
# EDGE / PATH HELPERS
# ============================================================


def test_edge_ids_between_returns_matching_ids(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 1, "uses"),
        make_relationship(3, 2, 3, "owns"),
    ]

    result = reasoner._edge_ids_between(
        relationships,
        1,
        2,
    )

    assert result == [1, 2]


def test_edge_ids_between_deduplicates_ids(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(1, 1, 2, "uses"),
    ]

    result = reasoner._edge_ids_between(
        relationships,
        1,
        2,
    )

    assert result == [1]


def test_path_edges_returns_edges_for_path(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(1, 1, 2, "contacted"),
        make_relationship(2, 2, 3, "uses"),
        make_relationship(3, 3, 4, "owns"),
    ]

    result = reasoner._path_edges(
        relationships,
        [1, 2, 3],
    )

    assert result == [1, 2]


# ============================================================
# DUPLICATE REMOVAL
# ============================================================


def test_remove_duplicates_preserves_first(
    reasoner: IntelligenceReasoner,
) -> None:
    first = make_finding(
        title="Same",
        confidence=0.70,
        entities=[1, 2],
        evidence=[3],
        relationships=[4],
    )

    duplicate = make_finding(
        title="Same",
        confidence=0.95,
        entities=[1, 2],
        evidence=[3],
        relationships=[4],
    )

    different = make_finding(
        title="Different",
        confidence=0.95,
        entities=[1, 2],
        evidence=[3],
        relationships=[4],
    )

    result = reasoner._remove_duplicates(
        [
            first,
            duplicate,
            different,
        ]
    )

    assert result == [
        first,
        different,
    ]


# ============================================================
# MAIN REASONING ENTRY POINT
# ============================================================


def test_reason_returns_empty_when_no_findings(
    reasoner: IntelligenceReasoner,
) -> None:
    graph_analysis = make_graph_analysis()

    result = reasoner.reason(
        findings=[],
        entities=[],
        evidence=[],
        relationships=[],
        graph_analysis=graph_analysis,
    )

    assert result == []


def test_reason_preserves_original_finding(
    reasoner: IntelligenceReasoner,
) -> None:
    original = make_finding(
        title="Original finding",
        confidence=0.91,
        entities=[1],
    )

    graph_analysis = make_graph_analysis(
        central_entities=[],
        connected_components=[],
        node_count=1,
        edge_count=0,
    )

    result = reasoner.reason(
        findings=[original],
        entities=[make_entity(1)],
        evidence=[],
        relationships=[],
        graph_analysis=graph_analysis,
    )

    assert result
    assert result[0] is original
    assert any(
        finding.title == "Original finding"
        for finding in result
    )

def test_articulation_reasoning_skips_entity_with_single_neighbor(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            2,
            "contacted",
            0.95,
        ),
    ]

    result = reasoner._reason_articulation_points(
        relationships=relationships,
        graph_analysis=SimpleNamespace(),
    )

    assert result == []

def test_typed_path_reinforcement_skips_duplicate_seen_key(
    reasoner: IntelligenceReasoner,
    monkeypatch,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            2,
            "contacted",
            0.95,
        ),
        make_relationship(
            2,
            1,
            3,
            "uses",
            0.95,
        ),
    ]

    # Normal _build_adjacency() returns sets, which naturally remove
    # duplicates. This deliberately supplies duplicate neighbors so
    # the defensive `if key in seen: continue` branch is exercised.
    monkeypatch.setattr(
        reasoner,
        "_build_adjacency",
        lambda _relationships: {
            1: [2, 3, 2, 3],
            2: set(),
            3: set(),
        },
    )

    result = reasoner._reason_typed_path_reinforcement(
        findings=[],
        relationships=relationships,
    )

    # The duplicate key must not create duplicate findings.
    assert len(result) == 1

def test_articulation_points_skip_entity_with_fewer_than_two_neighbors(
    reasoner: IntelligenceReasoner,
) -> None:
    relationships = [
        make_relationship(
            1,
            1,
            2,
            "contacted",
            0.95,
        ),
    ]

    result = reasoner._reason_articulation_points(
        relationships=relationships,
        graph_analysis=SimpleNamespace(),
    )

    assert result == []    
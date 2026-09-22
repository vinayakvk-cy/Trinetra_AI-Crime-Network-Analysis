from __future__ import annotations

from app.ai.intelligence.graph import (
    IntelligenceGraph,
    IntelligenceGraphNode,
)


def test_build_skips_relationship_with_invalid_entity_ids() -> None:
    graph = IntelligenceGraph()

    relationship = type(
        "Relationship",
        (),
        {
            "source_entity_id": "not-an-int",
            "target_entity_id": "2",
            "relationship_type": "knows",
        },
    )()

    graph.build(relationships=[relationship])

    assert graph.nodes == {}
    assert graph.edges == []


def test_find_path_returns_zero_distance_for_same_entity() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(entity_id=1)

    result = graph.find_path(
        source_entity_id=1,
        target_entity_id=1,
    )

    assert result is not None
    assert result.source_entity_id == 1
    assert result.target_entity_id == 1
    assert result.path == [1]
    assert result.distance == 0


def test_get_neighbors_returns_empty_for_missing_entity() -> None:
    graph = IntelligenceGraph()

    assert graph.get_neighbors(999) == []


def test_get_degree_returns_zero_for_missing_entity() -> None:
    graph = IntelligenceGraph()

    assert graph.get_degree(999) == 0


def test_build_skips_relationship_with_missing_entity_id() -> None:
    graph = IntelligenceGraph()

    relationship = type(
        "Relationship",
        (),
        {
            "source_entity_id": None,
            "target_entity_id": 2,
            "relationship_type": "knows",
        },
    )()

    graph.build(relationships=[relationship])

    assert graph.nodes == {}
    assert graph.edges == []


def test_build_skips_relationship_with_invalid_target_id() -> None:
    graph = IntelligenceGraph()

    relationship = type(
        "Relationship",
        (),
        {
            "source_entity_id": 1,
            "target_entity_id": "not-an-int",
            "relationship_type": "knows",
        },
    )()

    graph.build(relationships=[relationship])

    assert graph.nodes == {}
    assert graph.edges == []

def test_build_creates_nodes_connections_and_edge() -> None:
    graph = IntelligenceGraph()

    relationship = type(
        "Relationship",
        (),
        {
            "source_entity_id": 1,
            "target_entity_id": 2,
            "relationship_type": "knows",
        },
    )()

    graph.build(relationships=[relationship])

    assert set(graph.nodes) == {1, 2}

    assert graph.nodes[1].connected_entity_ids == {2}
    assert graph.nodes[2].connected_entity_ids == {1}

    assert graph.nodes[1].relationship_count == 1
    assert graph.nodes[2].relationship_count == 1

    assert graph.edges == [(1, 2, "knows")]

def test_analyze_returns_graph_statistics() -> None:
    graph = IntelligenceGraph()

    relationship_one = type(
        "Relationship",
        (),
        {
            "source_entity_id": 1,
            "target_entity_id": 2,
            "relationship_type": "knows",
        },
    )()

    relationship_two = type(
        "Relationship",
        (),
        {
            "source_entity_id": 2,
            "target_entity_id": 3,
            "relationship_type": "works_with",
        },
    )()

    graph.build(
        relationships=[
            relationship_one,
            relationship_two,
        ]
    )

    result = graph.analyze()

    assert result.node_count == 3
    assert result.edge_count == 2
    assert result.relationship_type_counts == {
        "knows": 1,
        "works_with": 1,
    }
    assert len(result.connected_components) == 1
    assert result.central_entities

def test_find_central_entities_returns_all_top_ties() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        relationship_count=3,
        connected_entity_ids={2, 3, 4},
    )
    graph.nodes[2] = IntelligenceGraphNode(
        entity_id=2,
        relationship_count=3,
        connected_entity_ids={1, 3, 4},
    )
    graph.nodes[3] = IntelligenceGraphNode(
        entity_id=3,
        relationship_count=1,
        connected_entity_ids={1},
    )

    result = graph._find_central_entities()

    assert set(result) == {1, 2}

def test_find_connected_components_skips_missing_connected_node() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids={999},
    )

    result = graph._find_connected_components()

    assert result == [[1, 999]]

def test_find_path_returns_shortest_path() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids={2},
    )
    graph.nodes[2] = IntelligenceGraphNode(
        entity_id=2,
        connected_entity_ids={1, 3},
    )
    graph.nodes[3] = IntelligenceGraphNode(
        entity_id=3,
        connected_entity_ids={2},
    )

    result = graph.find_path(
        source_entity_id=1,
        target_entity_id=3,
    )

    assert result is not None
    assert result.source_entity_id == 1
    assert result.target_entity_id == 3
    assert result.path == [1, 2, 3]
    assert result.distance == 2


def test_find_path_returns_none_when_entities_are_disconnected() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids=set(),
    )
    graph.nodes[2] = IntelligenceGraphNode(
        entity_id=2,
        connected_entity_ids=set(),
    )

    result = graph.find_path(
        source_entity_id=1,
        target_entity_id=2,
    )

    assert result is None


def test_find_path_skips_missing_connected_node() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids={999},
    )

    graph.nodes[2] = IntelligenceGraphNode(
        entity_id=2,
        connected_entity_ids=set(),
    )

    result = graph.find_path(
        source_entity_id=1,
        target_entity_id=2,
    )

    assert result is None

def test_get_neighbors_returns_sorted_connected_entities() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids={5, 2, 9},
    )

    assert graph.get_neighbors(1) == [2, 5, 9]


def test_get_degree_returns_number_of_connected_entities() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(
        entity_id=1,
        connected_entity_ids={5, 2, 9},
    )

    assert graph.get_degree(1) == 3

def test_find_central_entities_returns_empty_for_empty_graph() -> None:
    graph = IntelligenceGraph()

    assert graph._find_central_entities() == []


def test_find_path_returns_none_when_entity_is_missing() -> None:
    graph = IntelligenceGraph()

    graph.nodes[1] = IntelligenceGraphNode(entity_id=1)

    result = graph.find_path(
        source_entity_id=1,
        target_entity_id=999,
    )

    assert result is None
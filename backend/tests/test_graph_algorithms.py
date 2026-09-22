from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.graph.graph_algorithms import GraphAlgorithms
from app.graph.graph_queries import GraphQueries
from app.analytics.graph_algorithms import (
    EntityGraphProfile,
    GraphAnalytics,
    GraphMetric,
    analyze_entity,
    analyze_path,
)


# ============================================================
# DATACLASS TESTS
# ============================================================


def test_graph_metric_to_dict() -> None:
    metric = GraphMetric(
        metric_name="total_degree",
        value=5,
        description="Total number of direct graph connections.",
        entity_type="person",
        entity_value="Alice",
        metadata={"source": "test"},
    )

    result = metric.to_dict()

    assert result == {
        "metric_name": "total_degree",
        "value": 5,
        "description": "Total number of direct graph connections.",
        "entity_type": "person",
        "entity_value": "Alice",
        "metadata": {"source": "test"},
    }


def test_entity_graph_profile_to_dict() -> None:
    metric = GraphMetric(
        metric_name="total_degree",
        value=3,
        description="Total connections.",
        entity_type="person",
        entity_value="Alice",
    )

    profile = EntityGraphProfile(
        entity_type="person",
        entity_value="Alice",
        total_degree=3,
        incoming_degree=1,
        outgoing_degree=2,
        neighbor_count=2,
        relationship_count=2,
        metrics=[metric],
        connections=[
            {"relationship_type": "contacted"}
        ],
    )

    result = profile.to_dict()

    assert result == {
        "entity_type": "person",
        "entity_value": "Alice",
        "total_degree": 3,
        "incoming_degree": 1,
        "outgoing_degree": 2,
        "neighbor_count": 2,
        "relationship_count": 2,
        "metrics": [
            metric.to_dict()
        ],
        "connections": [
            {"relationship_type": "contacted"}
        ],
    }


# ============================================================
# FIXTURE
# ============================================================


@pytest.fixture
def analytics() -> GraphAnalytics:
    client = MagicMock()

    service = GraphAnalytics.__new__(
        GraphAnalytics
    )

    service.client = client
    service.algorithms = MagicMock()
    service.queries = MagicMock()

    return service


# ============================================================
# ENTITY PROFILE
# ============================================================


def test_analyze_entity_returns_none_when_degree_missing(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = None

    result = analytics.analyze_entity(
        entity_type="person",
        value="Alice",
    )

    assert result is None

    analytics.algorithms.node_degree.assert_called_once_with(
        entity_type="person",
        value="Alice",
    )


def test_analyze_entity_builds_profile(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = {
        "total_degree": 5,
        "incoming_degree": 2,
        "outgoing_degree": 3,
    }

    analytics.queries.get_relationships.return_value = [
        {
            "relationship_type": "contacted",
        },
        {
            "relationship_type": "uses",
        },
    ]

    analytics.queries.get_neighbors.return_value = [
        {
            "entity_type": "person",
            "entity_value": "Bob",
        },
        {
            "entity_type": "device",
            "entity_value": "D1",
        },
    ]

    result = analytics.analyze_entity(
        entity_type="person",
        value="Alice",
    )

    assert result is not None
    assert result.entity_type == "person"
    assert result.entity_value == "Alice"
    assert result.total_degree == 5
    assert result.incoming_degree == 2
    assert result.outgoing_degree == 3
    assert result.neighbor_count == 2
    assert result.relationship_count == 2
    assert len(result.metrics) == 4
    assert result.connections == [
        {"relationship_type": "contacted"},
        {"relationship_type": "uses"},
    ]


def test_analyze_entity_handles_missing_degree_values(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = {}

    result = analytics.analyze_entity(
        entity_type="person",
        value="Alice",
    )

    assert result is None


# ============================================================
# TOP CONNECTED
# ============================================================


def test_top_connected_entities_delegates(
    analytics: GraphAnalytics,
) -> None:
    expected = [
        {
            "entity_type": "person",
            "entity_value": "Alice",
            "degree": 10,
        }
    ]

    analytics.algorithms.most_connected_entities.return_value = (
        expected
    )

    result = analytics.top_connected_entities(
        limit=5,
        entity_type="person",
    )

    assert result == expected

    analytics.algorithms.most_connected_entities.assert_called_once_with(
        limit=5,
        entity_type="person",
    )


# ============================================================
# CONNECTION SCORE
# ============================================================


def test_connection_score_returns_zero_when_profile_missing(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = None

    result = analytics.connection_score(
        entity_type="person",
        value="Unknown",
    )

    assert result == 0.0


def test_connection_score_returns_zero_when_no_highest_entity(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = {
        "total_degree": 5,
    }

    analytics.queries.get_relationships.return_value = []
    analytics.queries.get_neighbors.return_value = []

    analytics.algorithms.most_connected_entities.return_value = []

    result = analytics.connection_score(
        entity_type="person",
        value="Alice",
    )

    assert result == 0.0


def test_connection_score_normalizes_against_highest_degree(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = {
        "total_degree": 5,
        "incoming_degree": 2,
        "outgoing_degree": 3,
    }

    analytics.queries.get_relationships.return_value = []
    analytics.queries.get_neighbors.return_value = []

    analytics.algorithms.most_connected_entities.return_value = [
        {
            "entity_type": "person",
            "entity_value": "Bob",
            "degree": 10,
        }
    ]

    result = analytics.connection_score(
        entity_type="person",
        value="Alice",
    )

    assert result == 0.5


def test_connection_score_is_capped_at_one(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.node_degree.return_value = {
        "total_degree": 20,
    }

    analytics.queries.get_relationships.return_value = []
    analytics.queries.get_neighbors.return_value = []

    analytics.algorithms.most_connected_entities.return_value = [
        {
            "degree": 10,
        }
    ]

    result = analytics.connection_score(
        entity_type="person",
        value="Alice",
    )

    assert result == 1.0


# ============================================================
# RELATIONSHIP DIVERSITY
# ============================================================


def test_relationship_diversity_empty(
    analytics: GraphAnalytics,
) -> None:
    analytics.queries.get_relationships.return_value = []

    result = analytics.relationship_diversity(
        entity_type="person",
        value="Alice",
    )

    assert result == {
        "relationship_types": 0,
        "relationships": 0,
        "types": [],
    }


def test_relationship_diversity_counts_unique_types(
    analytics: GraphAnalytics,
) -> None:
    analytics.queries.get_relationships.return_value = [
        {"relationship_type": "uses"},
        {"relationship_type": "contacted"},
        {"relationship_type": "uses"},
        {"relationship_type": None},
    ]

    result = analytics.relationship_diversity(
        entity_type="person",
        value="Alice",
    )

    assert result == {
        "relationship_types": 2,
        "relationships": 4,
        "types": [
            "contacted",
            "uses",
        ],
    }


# ============================================================
# NEIGHBORHOOD
# ============================================================


def test_analyze_neighborhood_builds_distribution(
    analytics: GraphAnalytics,
) -> None:
    analytics.queries.get_neighbors.return_value = [
        {"entity_type": "person"},
        {"entity_type": "person"},
        {"entity_type": "device"},
        {"entity_type": None},
    ]

    analytics.algorithms.neighborhood_density.return_value = {
        "density": 0.75,
    }

    result = analytics.analyze_neighborhood(
        entity_type="person",
        value="Alice",
        depth=4,
    )

    assert result == {
        "entity_type": "person",
        "entity_value": "Alice",
        "depth": 4,
        "neighbor_count": 4,
        "entity_type_distribution": {
            "person": 2,
            "device": 1,
        },
        "density": 0.75,
        "neighbors": [
            {"entity_type": "person"},
            {"entity_type": "person"},
            {"entity_type": "device"},
            {"entity_type": None},
        ],
    }

    analytics.algorithms.neighborhood_density.assert_called_once_with(
        entity_type="person",
        value="Alice",
        depth=3,
    )


# ============================================================
# SHARED ENTITY
# ============================================================


def test_shared_entity_analysis(
    analytics: GraphAnalytics,
) -> None:
    people = [
        {"entity_type": "person", "entity_value": "Alice"},
        {"entity_type": "person", "entity_value": "Bob"},
    ]

    analytics.queries.find_people_sharing_entity.return_value = (
        people
    )

    result = analytics.shared_entity_analysis(
        entity_type="phone",
        value="555",
    )

    assert result == {
        "entity_type": "phone",
        "entity_value": "555",
        "person_count": 2,
        "people": people,
    }

    analytics.queries.find_people_sharing_entity.assert_called_once_with(
        entity_type="phone",
        entity_value="555",
    )


# ============================================================
# OVERVIEW
# ============================================================


def test_overview(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.relationship_distribution.return_value = {
        "contacted": 5,
    }

    analytics.algorithms.entity_distribution.return_value = {
        "person": 3,
    }

    result = analytics.overview()

    assert result == {
        "entity_distribution": {
            "person": 3,
        },
        "relationship_distribution": {
            "contacted": 5,
        },
    }


# ============================================================
# STRUCTURAL OUTLIERS
# ============================================================


def test_structural_outliers_filters_zero_degree(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.most_connected_entities.return_value = [
        {
            "entity_value": "Alice",
            "degree": 10,
        },
        {
            "entity_value": "Bob",
            "degree": 0,
        },
        {
            "entity_value": "Carol",
            "degree": None,
        },
    ]

    result = analytics.structural_outliers(
        limit=3
    )

    assert result == [
        {
            "entity_value": "Alice",
            "degree": 10,
            "observation": "High graph connectivity",
        }
    ]


# ============================================================
# BRIDGE ANALYSIS
# ============================================================


def test_bridge_analysis_delegates(
    analytics: GraphAnalytics,
) -> None:
    expected = [
        {
            "entity_type": "person",
            "entity_value": "Alice",
        }
    ]

    analytics.algorithms.bridge_entities.return_value = (
        expected
    )

    result = analytics.bridge_analysis(
        limit=7
    )

    assert result == expected

    analytics.algorithms.bridge_entities.assert_called_once_with(
        limit=7
    )


# ============================================================
# PATH ANALYSIS
# ============================================================


def test_path_analysis_returns_none_when_no_path(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.shortest_path.return_value = None

    result = analytics.path_analysis(
        source_type="person",
        source_value="Alice",
        target_type="device",
        target_value="D1",
    )

    assert result is None


def test_path_analysis_builds_result(
    analytics: GraphAnalytics,
) -> None:
    analytics.algorithms.shortest_path.return_value = {
        "distance": 3,
        "nodes": ["Alice", "Phone", "Bob", "D1"],
        "relationships": [
            "uses",
            "shared",
            "uses",
        ],
    }

    result = analytics.path_analysis(
        source_type="person",
        source_value="Alice",
        target_type="device",
        target_value="D1",
        max_depth=5,
    )

    assert result == {
        "source": {
            "type": "person",
            "value": "Alice",
        },
        "target": {
            "type": "device",
            "value": "D1",
        },
        "distance": 3,
        "nodes": [
            "Alice",
            "Phone",
            "Bob",
            "D1",
        ],
        "relationships": [
            "uses",
            "shared",
            "uses",
        ],
        "connected": True,
    }

    analytics.algorithms.shortest_path.assert_called_once_with(
        source_type="person",
        source_value="Alice",
        target_type="device",
        target_value="D1",
        max_depth=5,
    )


# ============================================================
# CONVENIENCE WRAPPERS
# ============================================================


def test_analyze_entity_convenience_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()

    monkeypatch.setattr(
        "app.analytics.graph_algorithms.GraphAnalytics",
        lambda client: analytics,
    )

    expected = MagicMock()

    analytics.analyze_entity.return_value = expected

    client = MagicMock()

    result = analyze_entity(
        client=client,
        entity_type="person",
        value="Alice",
    )

    assert result is expected

    analytics.analyze_entity.assert_called_once_with(
        entity_type="person",
        value="Alice",
    )


def test_analyze_path_convenience_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analytics = MagicMock()

    monkeypatch.setattr(
        "app.analytics.graph_algorithms.GraphAnalytics",
        lambda client: analytics,
    )

    expected = {
        "connected": True,
    }

    analytics.path_analysis.return_value = expected

    client = MagicMock()

    result = analyze_path(
        client=client,
        source_type="person",
        source_value="Alice",
        target_type="device",
        target_value="D1",
    )

    assert result == expected

    analytics.path_analysis.assert_called_once_with(
        source_type="person",
        source_value="Alice",
        target_type="device",
        target_value="D1",
    )

def test_graph_analytics_initializes_dependencies() -> None:
    client = MagicMock()

    analytics = GraphAnalytics(client)

    assert analytics.client is client
    assert isinstance(
        analytics.algorithms,
        GraphAlgorithms,
    )
    assert isinstance(
        analytics.queries,
        GraphQueries,
    )

def test_connection_score_returns_zero_when_maximum_degree_is_zero(
    analytics,
) -> None:
    analytics.algorithms.most_connected_entities.return_value = [
        {"degree": 0}
    ]

    profile = EntityGraphProfile(
        entity_type="person",
        entity_value="Alice",
        total_degree=5,
        incoming_degree=2,
        outgoing_degree=3,
    )

    analytics.analyze_entity = MagicMock(return_value=profile)

    score = analytics.connection_score("person", "Alice")

    assert score == 0.0
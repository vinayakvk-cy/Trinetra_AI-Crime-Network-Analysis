from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# GRAPH NODE
# ============================================================


@dataclass
class IntelligenceGraphNode:
    """
    Represents one entity inside the intelligence graph.
    """

    entity_id: int

    relationship_count: int = 0

    connected_entity_ids: set[int] = field(
        default_factory=set
    )


# ============================================================
# GRAPH PATH
# ============================================================


@dataclass
class IntelligenceGraphPath:
    """
    Represents a path between two entities.
    """

    source_entity_id: int

    target_entity_id: int

    path: list[int] = field(
        default_factory=list
    )

    distance: int = 0


# ============================================================
# GRAPH ANALYSIS RESULT
# ============================================================


@dataclass
class IntelligenceGraphAnalysis:
    """
    Result produced by the intelligence graph analyzer.
    """

    node_count: int = 0

    edge_count: int = 0

    connected_components: list[list[int]] = field(
        default_factory=list
    )

    central_entities: list[int] = field(
        default_factory=list
    )

    relationship_type_counts: dict[str, int] = field(
        default_factory=dict
    )


# ============================================================
# INTELLIGENCE GRAPH
# ============================================================


class IntelligenceGraph:
    """
    Builds and analyzes an investigation relationship graph.

    The graph is intentionally independent from SQLAlchemy.

    Input:

        EntityRelationship records

    Graph:

        Entity A
            |
            | relationship
            |
        Entity B

    The graph can later support:

        - indirect relationship detection
        - entity centrality
        - relationship paths
        - clusters
        - connected components
        - network analysis
        - suspicious graph patterns
    """

    def __init__(self) -> None:

        self.nodes: dict[
            int,
            IntelligenceGraphNode,
        ] = {}

        self.edges: list[
            tuple[int, int, str]
        ] = []

    # ========================================================
    # BUILD GRAPH
    # ========================================================

    def build(
        self,
        *,
        relationships: list[Any],
    ) -> None:
        """
        Build the graph from relationship records.
        """

        self.nodes.clear()
        self.edges.clear()

        for relationship in relationships:

            source_id = getattr(
                relationship,
                "source_entity_id",
                None,
            )

            target_id = getattr(
                relationship,
                "target_entity_id",
                None,
            )

            relationship_type = getattr(
                relationship,
                "relationship_type",
                None,
            )

            if (
                source_id is None
                or target_id is None
            ):
                continue

            try:
                source_id = int(source_id)
                target_id = int(target_id)
            except (
                TypeError,
                ValueError,
            ):
                continue

            relationship_type_value = getattr(
                relationship_type,
                "value",
                str(relationship_type)
                if relationship_type is not None
                else "unknown",
            )

            # ------------------------------------------------
            # CREATE SOURCE NODE
            # ------------------------------------------------

            source_node = self.nodes.setdefault(
                source_id,
                IntelligenceGraphNode(
                    entity_id=source_id
                ),
            )

            # ------------------------------------------------
            # CREATE TARGET NODE
            # ------------------------------------------------

            target_node = self.nodes.setdefault(
                target_id,
                IntelligenceGraphNode(
                    entity_id=target_id
                ),
            )

            # ------------------------------------------------
            # CONNECT NODES
            # ------------------------------------------------

            source_node.connected_entity_ids.add(
                target_id
            )

            target_node.connected_entity_ids.add(
                source_id
            )

            source_node.relationship_count += 1
            target_node.relationship_count += 1

            # ------------------------------------------------
            # STORE EDGE
            # ------------------------------------------------

            self.edges.append(
                (
                    source_id,
                    target_id,
                    relationship_type_value,
                )
            )

    # ========================================================
    # ANALYZE GRAPH
    # ========================================================

    def analyze(self) -> IntelligenceGraphAnalysis:
        """
        Analyze the currently built graph.
        """

        relationship_type_counter: Counter[
            str
        ] = Counter()

        for (
            _source_id,
            _target_id,
            relationship_type,
        ) in self.edges:

            relationship_type_counter[
                relationship_type
            ] += 1

        central_entities = self._find_central_entities()

        components = self._find_connected_components()

        return IntelligenceGraphAnalysis(
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            connected_components=components,
            central_entities=central_entities,
            relationship_type_counts=dict(
                relationship_type_counter
            ),
        )

    # ========================================================
    # CENTRAL ENTITIES
    # ========================================================

    def _find_central_entities(
        self,
    ) -> list[int]:
        """
        Find entities with the highest number of connections.
        """

        if not self.nodes:
            return []

        ranked = sorted(
            self.nodes.values(),
            key=lambda node: (
                node.relationship_count,
                len(
                    node.connected_entity_ids
                ),
            ),
            reverse=True,
        )

        # Return entities tied for the top
        # relationship count.
        highest_count = ranked[0].relationship_count

        return [
            node.entity_id
            for node in ranked
            if node.relationship_count
            == highest_count
        ]

    # ========================================================
    # CONNECTED COMPONENTS
    # ========================================================

    def _find_connected_components(
        self,
    ) -> list[list[int]]:
        """
        Find groups of entities connected to one another.
        """

        visited: set[int] = set()

        components: list[list[int]] = []

        for entity_id in self.nodes:

            if entity_id in visited:
                continue

            component: list[int] = []

            queue: deque[int] = deque(
                [entity_id]
            )

            visited.add(entity_id)

            while queue:

                current = queue.popleft()

                component.append(current)

                node = self.nodes.get(
                    current
                )

                if node is None:
                    continue

                for connected_id in (
                    node.connected_entity_ids
                ):

                    if connected_id in visited:
                        continue

                    visited.add(
                        connected_id
                    )

                    queue.append(
                        connected_id
                    )

            components.append(
                sorted(component)
            )

        return components

    # ========================================================
    # FIND PATH
    # ========================================================

    def find_path(
        self,
        *,
        source_entity_id: int,
        target_entity_id: int,
    ) -> IntelligenceGraphPath | None:
        """
        Find the shortest relationship path between two entities.

        Uses breadth-first search.

        Example:

            Entity 1
                ↓
            Entity 2
                ↓
            Entity 3

        Path:

            [1, 2, 3]
        """

        if (
            source_entity_id not in self.nodes
            or target_entity_id not in self.nodes
        ):
            return None

        if (
            source_entity_id
            == target_entity_id
        ):
            return IntelligenceGraphPath(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                path=[
                    source_entity_id
                ],
                distance=0,
            )

        queue: deque[
            tuple[int, list[int]]
        ] = deque()

        queue.append(
            (
                source_entity_id,
                [source_entity_id],
            )
        )

        visited: set[int] = {
            source_entity_id
        }

        while queue:

            current_id, current_path = (
                queue.popleft()
            )

            node = self.nodes.get(
                current_id
            )

            if node is None:
                continue

            for connected_id in (
                node.connected_entity_ids
            ):

                if connected_id in visited:
                    continue

                next_path = [
                    *current_path,
                    connected_id,
                ]

                if (
                    connected_id
                    == target_entity_id
                ):
                    return IntelligenceGraphPath(
                        source_entity_id=(
                            source_entity_id
                        ),
                        target_entity_id=(
                            target_entity_id
                        ),
                        path=next_path,
                        distance=(
                            len(next_path) - 1
                        ),
                    )

                visited.add(
                    connected_id
                )

                queue.append(
                    (
                        connected_id,
                        next_path,
                    )
                )

        return None

    # ========================================================
    # GET NEIGHBORS
    # ========================================================

    def get_neighbors(
        self,
        entity_id: int,
    ) -> list[int]:
        """
        Return entities directly connected to an entity.
        """

        node = self.nodes.get(
            entity_id
        )

        if node is None:
            return []

        return sorted(
            node.connected_entity_ids
        )

    # ========================================================
    # DEGREE
    # ========================================================

    def get_degree(
        self,
        entity_id: int,
    ) -> int:
        """
        Return the number of unique entities connected
        to the supplied entity.
        """

        node = self.nodes.get(
            entity_id
        )

        if node is None:
            return 0

        return len(
            node.connected_entity_ids
        )


# ============================================================
# DEFAULT GRAPH
# ============================================================


intelligence_graph = IntelligenceGraph()
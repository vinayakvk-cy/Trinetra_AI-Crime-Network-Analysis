from __future__ import annotations

from dataclasses import dataclass
from unittest import result

import pytest

from app.ai.intelligence.engine import intelligence_engine
from app.ai.intelligence.models import IntelligenceSeverity


@dataclass
class RelationshipFixture:
    id: int
    source_entity_id: int
    target_entity_id: int
    relationship_type: str
    confidence: float
    evidence_id: int | None = None


@dataclass
class EntityFixture:
    id: int
    name: str


@dataclass
class EvidenceFixture:
    id: int
    description: str


def make_entity(entity_id: int, name: str) -> EntityFixture:
    return EntityFixture(id=entity_id, name=name)


def make_relationship(
    relationship_id: int,
    source_id: int,
    target_id: int,
    relationship_type: str,
    confidence: float,
    evidence_id: int | None = None,
) -> RelationshipFixture:
    return RelationshipFixture(
        id=relationship_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence_id=evidence_id,
    )


def analyze(
    *,
    investigation_id: int = 1,
    entities: list[EntityFixture] | None = None,
    evidence: list[EvidenceFixture] | None = None,
    relationships: list[RelationshipFixture] | None = None,
):
    return intelligence_engine.analyze_investigation(
        investigation_id=investigation_id,
        entities=entities or [],
        evidence=evidence or [],
        relationships=relationships or [],
    )


def test_empty_investigation_produces_low_risk() -> None:
    result = analyze()
    assert result.investigation_id == 1
    assert result.findings == []
    assert result.risk_assessment is not None
    assert result.risk_assessment.score == 0.0
    assert result.risk_assessment.severity == IntelligenceSeverity.LOW


def test_high_confidence_relationship_creates_finding() -> None:
    result = analyze(
        entities=[make_entity(1, "Rahul"), make_entity(2, "9876543210")],
        relationships=[make_relationship(1, 1, 2, "contacted", 0.95)],
    )
    matching = [f for f in result.findings if f.title == "High-confidence relationship"]
    assert matching
    assert matching[0].confidence == 0.95
    assert matching[0].supporting_relationship_ids == [1]


def test_low_confidence_relationship_does_not_create_high_confidence_finding() -> None:
    result = analyze(
        entities=[make_entity(1, "Rahul"), make_entity(2, "9876543210")],
        relationships=[make_relationship(1, 1, 2, "contacted", 0.50)],
    )
    matching = [f for f in result.findings if f.title == "High-confidence relationship"]
    assert matching == []


def test_evidence_supported_relationship_creates_evidence_finding() -> None:
    result = analyze(
        entities=[make_entity(1, "Rahul"), make_entity(2, "9876543210")],
        evidence=[EvidenceFixture(1, "CDR evidence supports the communication.")],
        relationships=[make_relationship(1, 1, 2, "contacted", 0.95, evidence_id=1)],
    )
    matching = [f for f in result.findings if f.title == "Relationship supported by evidence"]
    assert matching
    assert matching[0].supporting_evidence_ids == [1]
    assert matching[0].supporting_relationship_ids == [1]


def test_repeated_relationship_creates_repeated_relationship_finding() -> None:
    result = analyze(
        entities=[make_entity(1, "Rahul"), make_entity(2, "9876543210")],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.80),
            make_relationship(2, 1, 2, "contacted", 0.82),
        ],
    )
    matching = [f for f in result.findings if f.title == "Repeated relationship detected"]
    assert matching
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


def test_connected_entities_produce_graph_intelligence() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
            make_entity(3, "MH12AB1234"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.95),
            make_relationship(2, 1, 3, "uses", 0.87),
        ],
    )
    assert result.findings
    assert result.risk_assessment is not None
    assert result.analyzed_entity_count == 3
    assert result.analyzed_relationship_count == 2
    titles = {f.title for f in result.findings}
    assert "High-confidence relationship" in titles
    assert "Graph central entity detected" in titles
    assert "Connected intelligence cluster" in titles


def test_risk_score_is_always_bounded() -> None:
    result = analyze(
        entities=[make_entity(1, "Rahul"), make_entity(2, "9876543210")],
        relationships=[make_relationship(1, 1, 2, "contacted", 0.95)],
    )
    assert result.risk_assessment is not None
    assert 0.0 <= result.risk_assessment.score <= 1.0


def test_invalid_investigation_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        analyze(investigation_id=0)


def test_multiple_relationship_types_creates_indicator() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.95),
            make_relationship(2, 1, 2, "transferred", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Multiple relationship indicators"
    ]

    assert matching
    assert set(matching[0].supporting_entity_ids) == {1, 2}
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


def test_entity_activity_concentration_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "A"),
            make_entity(3, "B"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 1, 3, "uses", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Entity activity concentration"
    ]

    assert matching
    entity_finding = next(
        f for f in matching
        if 1 in f.supporting_entity_ids
    )

    assert 1 in entity_finding.supporting_entity_ids
    assert set(entity_finding.supporting_relationship_ids) == {1, 2}


def test_multiple_high_confidence_indicators_are_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "A"),
            make_entity(3, "B"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.95),
            make_relationship(2, 1, 3, "uses", 0.95),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Multiple high-confidence indicators"
    ]

    assert matching


def test_relationship_type_convergence_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "A"),
            make_entity(3, "B"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.95),
            make_relationship(2, 1, 3, "uses", 0.95),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Relationship type convergence"
    ]

    assert matching
    assert any(
        1 in f.supporting_entity_ids
        for f in matching
    )


def test_reciprocal_relationship_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "A"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 2, 1, "contacted", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Reciprocal relationship pattern"
    ]

    assert matching
    assert set(matching[0].supporting_entity_ids) == {1, 2}
    assert set(matching[0].supporting_relationship_ids) == {1, 2}


def test_triangle_pattern_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "A"),
            make_entity(2, "B"),
            make_entity(3, "C"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 2, 3, "contacted", 0.90),
            make_relationship(3, 1, 3, "contacted", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Closed triadic graph pattern"
    ]

    assert matching
    assert set(matching[0].supporting_entity_ids) == {1, 2, 3}
    assert set(matching[0].supporting_relationship_ids) == {1, 2, 3}


def test_hub_and_spoke_pattern_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "Hub"),
            make_entity(2, "A"),
            make_entity(3, "B"),
            make_entity(4, "C"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 1, 3, "contacted", 0.90),
            make_relationship(3, 1, 4, "contacted", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Hub-and-spoke graph pattern"
    ]

    assert matching
    assert 1 in matching[0].supporting_entity_ids
    assert {2, 3, 4}.issubset(
        set(matching[0].supporting_entity_ids)
    )


def test_indirect_relationship_path_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "A"),
            make_entity(2, "B"),
            make_entity(3, "C"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 2, 3, "uses", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Indirect relationship path detected"
    ]

    assert matching
    assert any(
        set(f.supporting_entity_ids) == {1, 2, 3}
        for f in matching
    )


def test_typed_multi_hop_pattern_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "A"),
            make_entity(2, "B"),
            make_entity(3, "C"),
        ],
        relationships=[
            make_relationship(1, 1, 2, "contacted", 0.90),
            make_relationship(2, 2, 3, "uses", 0.90),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Typed multi-hop graph pattern"
    ]

    assert matching
    assert any(
        set(f.supporting_entity_ids) == {1, 2, 3}
        for f in matching
    )


def test_evidence_reinforcement_is_detected() -> None:
    result = analyze(
        entities=[
            make_entity(1, "A"),
            make_entity(2, "B"),
        ],
        evidence=[
            EvidenceFixture(1, "Supporting evidence"),
        ],
        relationships=[
            make_relationship(
                1, 1, 2, "contacted", 0.95, evidence_id=1
            ),
            make_relationship(
                2, 1, 2, "contacted", 0.95, evidence_id=1
            ),
        ],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "Evidence reinforcement detected"
    ]

    assert matching
    assert matching[0].supporting_evidence_ids == [1]

def test_relationship_with_missing_type_is_ignored() -> None:
    relationship = type(
        "Relationship",
        (),
        {
            "id": 1,
            "source_entity_id": 1,
            "target_entity_id": 2,
            "relationship_type": None,
            "confidence": 0.95,
        },
    )()

    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
        ],
        relationships=[relationship],
    )

    assert result.findings == []
    assert result.analyzed_relationship_count == 1

def test_relationship_with_missing_confidence_is_ignored() -> None:
    relationship = type(
        "Relationship",
        (),
        {
            "id": 1,
            "source_entity_id": 1,
            "target_entity_id": 2,
            "relationship_type": "contacted",
            "confidence": None,
        },
    )()

    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
        ],
        relationships=[relationship],
    )

    matching = [
        f
        for f in result.findings
        if f.title == "High-confidence relationship"
    ]

    assert matching == []

def test_relationship_with_invalid_entity_ids_is_ignored() -> None:
    relationship = type(
        "Relationship",
        (),
        {
            "id": 1,
            "source_entity_id": None,
            "target_entity_id": 2,
            "relationship_type": "contacted",
            "confidence": 0.95,
        },
    )()

    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
        ],
        relationships=[relationship],
    )

    assert result.findings == []

def test_evidence_supported_relationship_without_type_uses_fallback() -> None:
    relationship = type(
        "Relationship",
        (),
        {
            "id": 1,
            "source_entity_id": 1,
            "target_entity_id": 2,
            "relationship_type": None,
            "confidence": 0.95,
            "evidence_id": 10,
        },
    )()

    result = analyze(
        entities=[
            make_entity(1, "Rahul"),
            make_entity(2, "9876543210"),
        ],
        evidence=[
            EvidenceFixture(
                id=10,
                description="Supporting evidence",
            )
        ],
        relationships=[relationship],
    )
    print(result.findings)
    assert result.findings

    

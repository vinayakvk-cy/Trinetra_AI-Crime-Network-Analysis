from __future__ import annotations

from dataclasses import dataclass

from app.ai.intelligence.confidence import IntelligenceConfidenceScorer


@dataclass
class EvidenceFixture:
    confidence: float | None = None


@dataclass
class FindingFixture:
    confidence: float


class TestIntelligenceConfidenceScorer:
    """
    Regression tests for IntelligenceConfidenceScorer.

    These tests lock down the current deterministic behavior before
    any future confidence-model improvements are introduced.
    """

    def setup_method(self) -> None:
        self.scorer = IntelligenceConfidenceScorer()

    # ========================================================
    # ENTITY CONFIDENCE
    # ========================================================

    def test_empty_entities_return_zero(self) -> None:
        result = self.scorer.calculate_entity_confidence([])

        assert result == 0.0

    def test_entity_confidence_is_averaged(self) -> None:
        result = self.scorer.calculate_entity_confidence(
            [
                {"confidence": 0.8},
                {"confidence": 0.6},
            ]
        )

        assert result == 0.7

    def test_entity_confidence_is_clamped(self) -> None:
        result = self.scorer.calculate_entity_confidence(
            [
                {"confidence": 2.0},
                {"confidence": -1.0},
            ]
        )

        assert result == 0.5

    def test_invalid_entity_confidence_is_treated_as_zero(self) -> None:
        result = self.scorer.calculate_entity_confidence(
            [
                {"confidence": "invalid"},
                {"confidence": 0.8},
            ]
        )

        assert result == 0.4

    def test_missing_entity_confidence_is_zero(self) -> None:
        result = self.scorer.calculate_entity_confidence(
            [
                {},
                {"confidence": 0.8},
            ]
        )

        assert result == 0.4

    # ========================================================
    # RELATIONSHIP CONFIDENCE
    # ========================================================

    def test_empty_relationships_return_zero(self) -> None:
        result = self.scorer.calculate_relationship_confidence([])

        assert result == 0.0

    def test_relationship_confidence_is_averaged(self) -> None:
        result = self.scorer.calculate_relationship_confidence(
            [
                {"confidence": 0.9},
                {"confidence": 0.7},
            ]
        )

        assert result == 0.8

    def test_relationship_confidence_is_clamped(self) -> None:
        result = self.scorer.calculate_relationship_confidence(
            [
                {"confidence": 2.0},
                {"confidence": -1.0},
            ]
        )

        assert result == 0.5

    def test_invalid_relationship_confidence_is_zero(self) -> None:
        result = self.scorer.calculate_relationship_confidence(
            [
                {"confidence": "invalid"},
                {"confidence": 0.8},
            ]
        )

        assert result == 0.4

    # ========================================================
    # EVIDENCE CONFIDENCE
    # ========================================================

    def test_empty_evidence_returns_zero(self) -> None:
        result = self.scorer.calculate_evidence_confidence([])

        assert result == 0.0

    def test_evidence_confidence_is_averaged(self) -> None:
        result = self.scorer.calculate_evidence_confidence(
            [
                EvidenceFixture(confidence=0.9),
                EvidenceFixture(confidence=0.7),
            ]
        )

        assert result == 0.8

    def test_evidence_confidence_is_clamped(self) -> None:
        result = self.scorer.calculate_evidence_confidence(
            [
                EvidenceFixture(confidence=2.0),
                EvidenceFixture(confidence=-1.0),
            ]
        )

        assert result == 0.5

    def test_evidence_without_confidence_uses_baseline(self) -> None:
        result = self.scorer.calculate_evidence_confidence(
            [
                object(),
                object(),
            ]
        )

        assert result == 0.60

    def test_evidence_with_mixed_confidence_ignores_missing_values(
        self,
    ) -> None:
        result = self.scorer.calculate_evidence_confidence(
            [
                EvidenceFixture(confidence=0.8),
                object(),
                EvidenceFixture (confidence=0.6),
            ]
        )

        assert result == 0.7

    # ========================================================
    # REASONING CONFIDENCE
    # ========================================================

    def test_empty_findings_return_zero(self) -> None:
        result = self.scorer.calculate_reasoning_confidence([])

        assert result == 0.0

    def test_reasoning_confidence_is_averaged(self) -> None:
        result = self.scorer.calculate_reasoning_confidence(
            [
                FindingFixture(confidence=0.9),
                FindingFixture(confidence=0.7),
            ]
        )

        assert result == 0.8

    def test_reasoning_confidence_is_clamped(self) -> None:
        result = self.scorer.calculate_reasoning_confidence(
            [
                FindingFixture(confidence=2.0),
                FindingFixture(confidence=-1.0),
            ]
        )

        assert result == 0.5

    def test_invalid_reasoning_confidence_is_zero(self) -> None:
        result = self.scorer.calculate_reasoning_confidence(
            [
                FindingFixture(confidence="invalid"),  # type: ignore[arg-type]
                FindingFixture(confidence=0.8),
            ]
        )

        assert result == 0.4

    # ========================================================
    # OVERALL CONFIDENCE
    # ========================================================

    def test_empty_inputs_produce_zero_overall_confidence(self) -> None:
        result = self.scorer.calculate_overall_confidence(
            entities=[],
            relationships=[],
            evidence=[],
            findings=[],
        )

        assert result == 0.0

    def test_overall_confidence_uses_current_weights(self) -> None:
        result = self.scorer.calculate_overall_confidence(
            entities=[
                {"confidence": 0.8},
            ],
            relationships=[
                {"confidence": 0.6},
            ],
            evidence=[
                EvidenceFixture(confidence=0.7),
            ],
            findings=[
                FindingFixture(confidence=0.9),
            ],
        )

        expected = (
            0.8 * 0.20
            + 0.6 * 0.30
            + 0.7 * 0.20
            + 0.9 * 0.30
        )

        assert result == round(expected, 3)

    def test_overall_confidence_is_bounded(self) -> None:
        result = self.scorer.calculate_overall_confidence(
            entities=[
                {"confidence": 2.0},
            ],
            relationships=[
                {"confidence": 2.0},
            ],
            evidence=[
                EvidenceFixture(confidence=2.0),
            ],
            findings=[
                FindingFixture(confidence=2.0),
            ],
        )

        assert 0.0 <= result <= 1.0
        assert result == 1.0

    def test_overall_confidence_with_no_entity_data(self) -> None:
        result = self.scorer.calculate_overall_confidence(
            entities=[],
            relationships=[
                {"confidence": 0.8},
            ],
            evidence=[
                EvidenceFixture(confidence=0.6),
            ],
            findings=[
                FindingFixture(confidence=0.9),
            ],
        )

        expected = (
            0.0 * 0.20
            + 0.8 * 0.30
            + 0.6 * 0.20
            + 0.9 * 0.30
        )

        assert result == round(expected, 3)


# ============================================================
# MODULE-LEVEL API
# ============================================================


def test_default_confidence_scorer_exists() -> None:
    from app.ai.intelligence.confidence import confidence_scorer

    assert confidence_scorer is not None
    assert isinstance(
        confidence_scorer,
        IntelligenceConfidenceScorer,
    )
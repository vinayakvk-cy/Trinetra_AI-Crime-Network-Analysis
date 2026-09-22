from __future__ import annotations

from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceSeverity,
)
from app.ai.intelligence.risk import IntelligenceRiskAnalyzer


def finding(
    *,
    title: str = "Test finding",
    severity: IntelligenceSeverity = IntelligenceSeverity.MEDIUM,
    confidence: float = 0.8,
    entity_ids: list[int] | None = None,
    evidence_ids: list[int] | None = None,
    relationship_ids: list[int] | None = None,
) -> IntelligenceFinding:
    return IntelligenceFinding(
        title=title,
        description="Synthetic finding for risk calibration testing.",
        severity=severity,
        confidence=confidence,
        supporting_entity_ids=entity_ids or [],
        supporting_evidence_ids=evidence_ids or [],
        supporting_relationship_ids=relationship_ids or [],
    )


def test_empty_findings_have_zero_low_risk() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([])

    assert result.score == 0.0
    assert result.severity == IntelligenceSeverity.LOW


def test_single_medium_confidence_finding_has_expected_score() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([
        finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.8,
        )
    ])

    assert result.score == 0.8
    assert result.severity == IntelligenceSeverity.HIGH


def test_single_critical_finding_can_reach_critical_risk() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([
        finding(
            severity=IntelligenceSeverity.CRITICAL,
            confidence=0.95,
        )
    ])

    assert result.score == 0.95
    assert result.severity == IntelligenceSeverity.CRITICAL


def test_low_confidence_low_severity_finding_stays_low() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([
        finding(
            severity=IntelligenceSeverity.LOW,
            confidence=0.2,
        )
    ])

    assert result.score == 0.2
    assert result.severity == IntelligenceSeverity.LOW


def test_mixed_findings_are_weighted_by_severity() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([
        finding(
            severity=IntelligenceSeverity.HIGH,
            confidence=0.9,
        ),
        finding(
            severity=IntelligenceSeverity.LOW,
            confidence=0.2,
        ),
    ])

    expected = ((0.75 * 0.9) + (0.25 * 0.2)) / (0.75 + 0.25)

    assert result.score == round(expected, 3)
    assert result.severity == IntelligenceSeverity.HIGH


def test_risk_score_is_always_bounded() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    findings = [
        finding(
            severity=IntelligenceSeverity.CRITICAL,
            confidence=1.0,
        )
        for _ in range(20)
    ]

    result = analyzer.assess(findings)

    assert 0.0 <= result.score <= 1.0


def test_more_correlated_findings_should_not_be_assumed_to_mean_more_independent_evidence() -> None:
    """
    Calibration guardrail.

    This test documents the current limitation of the risk analyzer:
    it receives findings only and therefore cannot distinguish independent
    signals from many correlated findings describing the same relationship.

    The expected behavior for the next calibration stage is that risk should
    eventually be based on independent signals rather than raw finding count.
    """
    analyzer = IntelligenceRiskAnalyzer()

    one_signal = [
        finding(
            title="Original relationship",
            severity=IntelligenceSeverity.HIGH,
            confidence=0.95,
            entity_ids=[1, 2],
            relationship_ids=[1],
        )
    ]

    derived_same_signal = one_signal + [
        finding(
            title=f"Derived finding {index}",
            severity=IntelligenceSeverity.HIGH,
            confidence=0.95,
            entity_ids=[1, 2],
            relationship_ids=[1],
        )
        for index in range(5)
    ]

    base_result = analyzer.assess(one_signal)
    derived_result = analyzer.assess(derived_same_signal)

    assert base_result.score == 0.95

    # Current implementation is expected to produce the same score here
    # because all findings have identical severity/confidence.
    # This test exposes the calibration boundary without changing behavior.
    assert derived_result.score == 0.95


def test_risk_explanation_contains_finding_count_and_score() -> None:
    analyzer = IntelligenceRiskAnalyzer()

    result = analyzer.assess([
        finding(
            severity=IntelligenceSeverity.HIGH,
            confidence=0.9,
        )
    ])

    assert "1 finding(s)" in result.explanation
    assert "0.900" in result.explanation
    assert "high" in result.explanation.lower()

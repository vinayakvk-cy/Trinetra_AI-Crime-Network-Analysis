from __future__ import annotations

from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceSeverity,
)
from app.ai.intelligence.risk import IntelligenceRiskAnalyzer


risk_analyzer = IntelligenceRiskAnalyzer()


def make_finding(
    *,
    severity: IntelligenceSeverity,
    confidence: float,
) -> IntelligenceFinding:

    return IntelligenceFinding(
        title="Test finding",
        description="Test intelligence finding",
        severity=severity,
        confidence=confidence,
    )


def run_test(name: str, findings: list[IntelligenceFinding]) -> None:

    result = risk_analyzer.assess(findings)

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(f"Score      : {result.score}")
    print(f"Severity   : {result.severity.value}")
    print(f"Explanation: {result.explanation}")


# ============================================================
# TEST 1 — EMPTY INVESTIGATION
# ============================================================

run_test(
    "TEST 1 — Empty investigation",
    [],
)


# ============================================================
# TEST 2 — LOW CONFIDENCE / LOW SEVERITY
# ============================================================

run_test(
    "TEST 2 — Low-risk finding",
    [
        make_finding(
            severity=IntelligenceSeverity.LOW,
            confidence=0.50,
        )
    ],
)


# ============================================================
# TEST 3 — MEDIUM FINDING
# ============================================================

run_test(
    "TEST 3 — Medium-risk finding",
    [
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.70,
        )
    ],
)


# ============================================================
# TEST 4 — HIGH-CONFIDENCE RELATIONSHIP
# ============================================================

run_test(
    "TEST 4 — High-risk finding",
    [
        make_finding(
            severity=IntelligenceSeverity.HIGH,
            confidence=0.95,
        )
    ],
)


# ============================================================
# TEST 5 — CRITICAL FINDING
# ============================================================

run_test(
    "TEST 5 — Critical finding",
    [
        make_finding(
            severity=IntelligenceSeverity.CRITICAL,
            confidence=0.95,
        )
    ],
)


# ============================================================
# TEST 6 — MULTIPLE FINDINGS
# ============================================================

run_test(
    "TEST 6 — Multiple findings",
    [
        make_finding(
            severity=IntelligenceSeverity.HIGH,
            confidence=0.95,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.80,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.75,
        ),
    ],
)


# ============================================================
# TEST 7 — CORRELATED FINDINGS
# ============================================================

run_test(
    "TEST 7 — Correlated findings",
    [
        make_finding(
            severity=IntelligenceSeverity.HIGH,
            confidence=0.95,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.90,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.85,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.80,
        ),
        make_finding(
            severity=IntelligenceSeverity.MEDIUM,
            confidence=0.80,
        ),
    ],
)


print("\n" + "=" * 60)
print("RISK TESTS COMPLETE")
print("=" * 60)
from __future__ import annotations

from dataclasses import dataclass

from app.ai.intelligence.engine import intelligence_engine


# ============================================================
# TEST OBJECTS
# ============================================================


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


# ============================================================
# SAMPLE DATA
# ============================================================


entities = [
    EntityFixture(
        id=1,
        name="Rahul",
    ),
    EntityFixture(
        id=2,
        name="9876543210",
    ),
    EntityFixture(
        id=3,
        name="MH12AB1234",
    ),
]


evidence = [
    EvidenceFixture(
        id=1,
        description=(
            "CDR evidence indicates communication "
            "between Rahul and the phone number."
        ),
    ),
]


relationships = [
    RelationshipFixture(
        id=1,
        source_entity_id=1,
        target_entity_id=2,
        relationship_type="contacted",
        confidence=0.95,
        evidence_id=1,
    ),
    
    RelationshipFixture(
        id=2,
        source_entity_id=1,
        target_entity_id=3,
        relationship_type="uses",
        confidence=0.87,
    ),
]


# ============================================================
# RUN INTELLIGENCE ENGINE
# ============================================================


result = intelligence_engine.analyze_investigation(
    investigation_id=1,
    entities=entities,
    evidence=evidence,
    relationships=relationships,
)


# ============================================================
# DISPLAY RESULT
# ============================================================


print("\n" + "=" * 60)
print("TRINETRA AI INTELLIGENCE ENGINE TEST")
print("=" * 60)


print("\nINVESTIGATION:")
print(result.investigation_id)


print("\nSUMMARY:")
print(result.summary)


print("\nANALYZED DATA:")
print("-" * 60)

print(
    f"Entities      : {result.analyzed_entity_count}"
)

print(
    f"Evidence      : {result.analyzed_evidence_count}"
)

print(
    f"Relationships : {result.analyzed_relationship_count}"
)


print("\nFINDINGS:")
print("-" * 60)


if not result.findings:

    print("No findings generated.")

else:

    for index, finding in enumerate(
        result.findings,
        start=1,
    ):

        print(
            f"\nFinding #{index}"
        )

        print(
            f"Title      : {finding.title}"
        )

        print(
            f"Severity   : "
            f"{finding.severity.value}"
        )

        print(
            f"Confidence : "
            f"{finding.confidence}"
        )

        print(
            f"Description: "
            f"{finding.description}"
        )

        print(
            f"Entities   : "
            f"{finding.supporting_entity_ids}"
        )

        print(
            f"Evidence   : "
            f"{finding.supporting_evidence_ids}"
        )

        print(
            f"Relations  : "
            f"{finding.supporting_relationship_ids}"
        )


print("\nRISK ASSESSMENT:")
print("-" * 60)


if result.risk_assessment:

    print(
        f"Score      : "
        f"{result.risk_assessment.score}"
    )

    print(
        f"Severity   : "
        f"{result.risk_assessment.severity.value}"
    )

    print(
        f"Explanation: "
        f"{result.risk_assessment.explanation}"
    )

else:

    print("No risk assessment generated.")


print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
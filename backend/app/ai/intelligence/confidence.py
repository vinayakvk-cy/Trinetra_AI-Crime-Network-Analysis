from __future__ import annotations

from typing import Any


class IntelligenceConfidenceScorer:
    """
    Calculates confidence scores for extracted intelligence.

    This is intentionally deterministic for now.

    Future versions can incorporate:
        - NLP model confidence
        - LLM confidence
        - source reliability
        - evidence quality
        - cross-source verification
        - temporal consistency
        - entity resolution confidence
        - relationship confidence
    """

    # ========================================================
    # ENTITY CONFIDENCE
    # ========================================================

    def calculate_entity_confidence(
        self,
        entities: list[dict[str, Any]],
    ) -> float:
        """
        Calculate average confidence of extracted entities.
        """

        if not entities:
            return 0.0

        values: list[float] = []

        for entity in entities:

            confidence = entity.get(
                "confidence",
                0.0,
            )

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            values.append(
                max(
                    0.0,
                    min(confidence, 1.0),
                )
            )

        if not values:
            return 0.0

        return sum(values) / len(values)

    # ========================================================
    # RELATIONSHIP CONFIDENCE
    # ========================================================

    def calculate_relationship_confidence(
        self,
        relationships: list[dict[str, Any]],
    ) -> float:
        """
        Calculate average confidence of extracted relationships.
        """

        if not relationships:
            return 0.0

        values: list[float] = []

        for relationship in relationships:

            confidence = relationship.get(
                "confidence",
                0.0,
            )

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            values.append(
                max(
                    0.0,
                    min(confidence, 1.0),
                )
            )

        if not values:
            return 0.0

        return sum(values) / len(values)

    # ========================================================
    # EVIDENCE CONFIDENCE
    # ========================================================

    def calculate_evidence_confidence(
        self,
        evidence: list[Any],
    ) -> float:
        """
        Calculate confidence based on available evidence.

        If evidence objects contain a confidence attribute,
        their average is used.

        Otherwise, the presence of evidence contributes a
        conservative baseline.
        """

        if not evidence:
            return 0.0

        values: list[float] = []

        for item in evidence:

            confidence = getattr(
                item,
                "confidence",
                None,
            )

            if confidence is None:
                continue

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                continue

            values.append(
                max(
                    0.0,
                    min(confidence, 1.0),
                )
            )

        if values:
            return sum(values) / len(values)

        # Evidence exists, but no explicit confidence
        # has been assigned yet.
        return 0.60

    # ========================================================
    # REASONING CONFIDENCE
    # ========================================================

    def calculate_reasoning_confidence(
        self,
        findings: list[Any],
    ) -> float:
        """
        Calculate confidence from intelligence findings.
        """

        if not findings:
            return 0.0

        values: list[float] = []

        for finding in findings:

            confidence = getattr(
                finding,
                "confidence",
                0.0,
            )

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            values.append(
                max(
                    0.0,
                    min(confidence, 1.0),
                )
            )

        if not values:
            return 0.0

        return sum(values) / len(values)

    # ========================================================
    # OVERALL CONFIDENCE
    # ========================================================

    def calculate_overall_confidence(
        self,
        *,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        evidence: list[Any],
        findings: list[Any],
    ) -> float:
        """
        Calculate the overall intelligence confidence.

        Current weighting:

            Entity confidence        → 20%
            Relationship confidence  → 30%
            Evidence confidence      → 20%
            Reasoning confidence     → 30%
        """

        entity_confidence = (
            self.calculate_entity_confidence(
                entities
            )
        )

        relationship_confidence = (
            self.calculate_relationship_confidence(
                relationships
            )
        )

        evidence_confidence = (
            self.calculate_evidence_confidence(
                evidence
            )
        )

        reasoning_confidence = (
            self.calculate_reasoning_confidence(
                findings
            )
        )

        score = (
            entity_confidence * 0.20
            + relationship_confidence * 0.30
            + evidence_confidence * 0.20
            + reasoning_confidence * 0.30
        )

        return round(
            max(
                0.0,
                min(score, 1.0),
            ),
            3,
        )


# ============================================================
# DEFAULT CONFIDENCE SCORER
# ============================================================

confidence_scorer = IntelligenceConfidenceScorer()
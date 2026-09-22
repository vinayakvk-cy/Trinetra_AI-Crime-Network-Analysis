from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceRiskAssessment,
    IntelligenceSeverity,
)


class IntelligenceRiskAnalyzer:
    """
    Calculates an overall investigation risk assessment.

    The model is correlation-aware.

    Important principle:

        More findings != automatically more risk.

    Multiple findings may describe the same underlying
    relationship, evidence record, or entity. Correlated
    findings therefore reinforce the same signal instead of
    being treated as completely independent evidence.

    The model considers:

        1. Finding severity
        2. Finding confidence
        3. Independent relationship support
        4. Independent evidence support
        5. Independent entity support
        6. Finding-family diversity
        7. Strongest underlying signals

    Compatibility rule:

        A single finding keeps its confidence as its risk score.

    For multiple independent findings, severity is used as a
    weighting factor when combining confidence values.

    Correlated findings describing the same underlying signal
    are treated as one signal so that derived findings cannot
    artificially inflate or dilute risk.
    """

    # ========================================================
    # CONFIGURATION
    # ========================================================

    SEVERITY_WEIGHTS = {
        IntelligenceSeverity.LOW: 0.25,
        IntelligenceSeverity.MEDIUM: 0.50,
        IntelligenceSeverity.HIGH: 0.75,
        IntelligenceSeverity.CRITICAL: 1.00,
    }

    # Correlated findings describe the same underlying signal.
    #
    # The first finding keeps its full contribution.
    # Additional findings are progressively discounted.
    #
    # These values are retained for compatibility with the
    # existing calibration model. Correlated findings are
    # ultimately represented by their strongest finding when
    # calculating the final independent signal score.
    CORRELATION_FACTORS = (
        1.00,
        0.45,
        0.25,
        0.15,
        0.10,
    )

    EVIDENCE_BONUS = 0.08
    RELATIONSHIP_BONUS = 0.06
    ENTITY_BONUS = 0.03
    FAMILY_BONUS = 0.025

    MAX_INDEPENDENT_BONUS = 0.20

    # ========================================================
    # MAIN ASSESSMENT
    # ========================================================

    def assess(
        self,
        findings: list[IntelligenceFinding],
    ) -> IntelligenceRiskAssessment:
        """
        Calculate the overall investigation risk score.

        Scoring contract:

            No findings
                -> 0.000

            One finding
                -> finding confidence

            Multiple independent findings
                -> severity-weighted confidence

            Multiple correlated findings
                -> treated as one underlying signal

        This keeps the scoring deterministic and prevents
        duplicate derived findings from artificially changing
        the investigation risk.
        """

        # ----------------------------------------------------
        # STEP 0
        # Empty investigation.
        # ----------------------------------------------------

        if not findings:
            return IntelligenceRiskAssessment(
                score=0.0,
                severity=IntelligenceSeverity.LOW,
                explanation=(
                    "No significant intelligence findings were detected."
                ),
            )

        # ----------------------------------------------------
        # STEP 1
        # Remove findings that cannot contribute meaningful
        # confidence.
        # ----------------------------------------------------

        valid_findings = [
            finding
            for finding in findings
            if self._valid_confidence(
                finding.confidence
            )
        ]

        if not valid_findings:
            return IntelligenceRiskAssessment(
                score=0.0,
                severity=IntelligenceSeverity.LOW,
                explanation=(
                    "No findings with meaningful confidence "
                    "were available for risk assessment."
                ),
            )

        # ----------------------------------------------------
        # STEP 2
        # Build independent signal groups.
        #
        # This preserves the correlation-aware behavior of the
        # original implementation.
        # ----------------------------------------------------

        signal_groups = self._build_signal_groups(
            valid_findings
        )

        # ----------------------------------------------------
        # STEP 3
        # Calculate one representative finding per signal.
        #
        # A correlated group must NOT be allowed to dilute the
        # strongest finding simply because more derived findings
        # were generated.
        #
        # Therefore the strongest finding represents the group.
        # ----------------------------------------------------

        representative_findings: list[
            IntelligenceFinding
        ] = []

        for group in signal_groups:

            if not group:
                continue

            strongest = max(
                group,
                key=self._finding_strength,
            )

            representative_findings.append(
                strongest
            )

        # Defensive fallback.
        if not representative_findings:
            representative_findings = valid_findings[:]

        # ----------------------------------------------------
        # STEP 4
        # Calculate the risk score.
        #
        # One finding:
        #
        #     score = confidence
        #
        # Multiple independent findings:
        #
        #     weighted confidence =
        #
        #       sum(severity_weight * confidence)
        #       --------------------------------
        #       sum(severity_weight)
        #
        # This is intentionally different from simply averaging
        # severity_weight * confidence.
        #
        # Example:
        #
        #     HIGH  0.9
        #     LOW   0.2
        #
        #     ((0.75 * 0.9) + (0.25 * 0.2))
        #     ----------------------------- = 0.725
        #              0.75 + 0.25
        # ----------------------------------------------------

        if len(representative_findings) == 1:
            score = self._single_signal_score(
                representative_findings[0]
            )
        else:
            score = self._weighted_multi_signal_score(
                representative_findings
            )

        # ----------------------------------------------------
        # STEP 5
        # Independent signal bonuses.
        #
        # IMPORTANT:
        #
        # These bonuses are retained for the broader
        # intelligence model, but they must never change the
        # score for a single finding.
        #
        # For multiple findings, the bonuses are applied only
        # when there is genuine supporting diversity.
        # ----------------------------------------------------

        if len(representative_findings) > 1:
            independent_bonus = (
                self._calculate_independent_signal_bonus(
                    findings=valid_findings,
                )
            )

            score += independent_bonus

        # ----------------------------------------------------
        # STEP 6
        # Clamp and round.
        # ----------------------------------------------------

        score = round(
            min(
                max(
                    score,
                    0.0,
                ),
                1.0,
            ),
            3,
        )

        # ----------------------------------------------------
        # STEP 7
        # Convert score to severity.
        # ----------------------------------------------------

        severity = self._score_to_severity(
            score
        )

        # ----------------------------------------------------
        # STEP 8
        # Build explanation.
        # ----------------------------------------------------

        explanation = self._build_explanation(
            findings=valid_findings,
            score=score,
            severity=severity,
        )

        return IntelligenceRiskAssessment(
            score=score,
            severity=severity,
            explanation=explanation,
        )

    # ========================================================
    # SINGLE SIGNAL SCORE
    # ========================================================

    def _single_signal_score(
        self,
        finding: IntelligenceFinding,
    ) -> float:
        """
        Return the score for a single independent signal.

        Compatibility requirement:

            risk score == confidence

        Severity still controls the resulting risk category,
        but it does not reduce the confidence score itself.

        Examples:

            LOW + 0.20
                -> 0.20

            MEDIUM + 0.80
                -> 0.80

            HIGH + 0.90
                -> 0.90

            CRITICAL + 0.95
                -> 0.95
        """

        return round(
            min(
                max(
                    float(
                        finding.confidence
                    ),
                    0.0,
                ),
                1.0,
            ),
            3,
        )

    # ========================================================
    # MULTI SIGNAL SCORE
    # ========================================================

    def _weighted_multi_signal_score(
        self,
        findings: list[IntelligenceFinding],
    ) -> float:
        """
        Calculate a severity-weighted confidence score.

        Each independent signal contributes according to its
        severity weight.

        Formula:

            sum(weight * confidence)
            ------------------------
                 sum(weight)

        This preserves the intended interpretation that a
        HIGH-severity finding should influence the final score
        more strongly than a LOW-severity finding.

        Example:

            HIGH  0.90
            LOW   0.20

            (0.75*0.90 + 0.25*0.20)
            ------------------------
                 0.75 + 0.25

            = 0.725
        """

        if not findings:
            return 0.0

        weighted_total = 0.0
        total_weight = 0.0

        for finding in findings:

            severity_weight = self._severity_weight(
                finding.severity
            )

            confidence = min(
                max(
                    float(
                        finding.confidence
                    ),
                    0.0,
                ),
                1.0,
            )

            weighted_total += (
                severity_weight
                * confidence
            )

            total_weight += severity_weight

        if total_weight <= 0.0:
            return 0.0

        return (
            weighted_total
            / total_weight
        )

    # ========================================================
    # SIGNAL GROUPING
    # ========================================================

    def _build_signal_groups(
        self,
        findings: list[IntelligenceFinding],
    ) -> list[list[IntelligenceFinding]]:
        """
        Group findings that appear to describe the same
        underlying intelligence signal.

        Relationship IDs are treated as the strongest
        correlation key.

        Evidence IDs are used when relationship IDs are absent.

        Findings without either are treated as independent
        signals.

        IMPORTANT:

        Findings that share a relationship ID are grouped
        together. This ensures that multiple derived findings
        describing the same relationship do not become multiple
        independent risk signals.
        """

        groups: list[
            list[IntelligenceFinding]
        ] = []

        relationship_groups: dict[
            int,
            list[IntelligenceFinding],
        ] = defaultdict(list)

        evidence_groups: dict[
            int,
            list[IntelligenceFinding],
        ] = defaultdict(list)

        unlinked_findings: list[
            IntelligenceFinding
        ] = []

        for finding in findings:

            relationship_ids = self._safe_ids(
                finding.supporting_relationship_ids
            )

            evidence_ids = self._safe_ids(
                finding.supporting_evidence_ids
            )

            # ------------------------------------------------
            # Relationship-backed finding.
            # ------------------------------------------------

            if relationship_ids:

                for relationship_id in relationship_ids:

                    relationship_groups[
                        relationship_id
                    ].append(
                        finding
                    )

            # ------------------------------------------------
            # Evidence-backed finding.
            # ------------------------------------------------

            elif evidence_ids:

                for evidence_id in evidence_ids:

                    evidence_groups[
                        evidence_id
                    ].append(
                        finding
                    )

            # ------------------------------------------------
            # No explicit relationship/evidence support.
            #
            # These findings are independent unless another
            # explicit signal connects them.
            # ------------------------------------------------

            else:

                unlinked_findings.append(
                    finding
                )

        # ----------------------------------------------------
        # Relationship-backed groups.
        # ----------------------------------------------------

        processed_relationship_findings: set[
            int
        ] = set()

        for group in relationship_groups.values():

            unique_group = self._unique_findings(
                group
            )

            if not unique_group:
                continue

            group_identity = {
                id(finding)
                for finding in unique_group
            }

            # A finding can share multiple relationship IDs.
            # Do not create duplicate signal groups for it.
            if (
                group_identity
                & processed_relationship_findings
            ):
                continue

            processed_relationship_findings.update(
                group_identity
            )

            groups.append(
                unique_group
            )

        # ----------------------------------------------------
        # Evidence-backed groups.
        # ----------------------------------------------------

        processed_evidence_findings: set[
            int
        ] = set()

        already_grouped = {
            id(finding)
            for group in groups
            for finding in group
        }

        for group in evidence_groups.values():

            unique_group = [
                finding
                for finding in self._unique_findings(
                    group
                )
                if id(finding)
                not in already_grouped
            ]

            if not unique_group:
                continue

            group_identity = {
                id(finding)
                for finding in unique_group
            }

            if (
                group_identity
                & processed_evidence_findings
            ):
                continue

            processed_evidence_findings.update(
                group_identity
            )

            groups.append(
                unique_group
            )

            already_grouped.update(
                group_identity
            )

        # ----------------------------------------------------
        # Unlinked findings.
        #
        # Each remains an independent signal.
        # ----------------------------------------------------

        for finding in unlinked_findings:

            if id(finding) in already_grouped:
                continue

            groups.append(
                [finding]
            )

        return groups

    # ========================================================
    # GROUP CORRELATION
    # ========================================================

    def _group_correlation_factor(
        self,
        index: int,
    ) -> float:
        """
        Return the diminishing-return factor for a finding
        inside a correlated signal group.

        Index 0 is always the strongest finding and therefore
        receives full contribution.

        This helper remains available for compatibility with
        the previous calibration implementation.
        """

        if index < 0:
            index = 0

        if index >= len(
            self.CORRELATION_FACTORS
        ):
            return self.CORRELATION_FACTORS[-1]

        return self.CORRELATION_FACTORS[
            index
        ]

    # ========================================================
    # FINDING STRENGTH
    # ========================================================

    def _finding_strength(
        self,
        finding: IntelligenceFinding,
    ) -> float:
        """
        Calculate the raw strength of a finding.

        This is:

            severity weight × confidence

        It is used to determine which finding is the strongest
        representative of a correlated signal.
        """

        severity_weight = self._severity_weight(
            finding.severity
        )

        confidence = min(
            max(
                float(
                    finding.confidence
                ),
                0.0,
            ),
            1.0,
        )

        return (
            severity_weight
            * confidence
        )

    # ========================================================
    # REINFORCEMENT FACTOR
    # ========================================================

    def _reinforcement_factor(
        self,
        index: int,
    ) -> float:
        """
        Diminishing-return factor for independent signal
        reinforcement.

        Retained as a utility for compatibility with the
        previous risk model.
        """

        factors = {
            1: 0.35,
            2: 0.25,
            3: 0.18,
            4: 0.12,
            5: 0.08,
            6: 0.05,
        }

        return factors.get(
            index,
            0.03,
        )

    # ========================================================
    # INDEPENDENT SIGNAL BONUS
    # ========================================================

    def _calculate_independent_signal_bonus(
        self,
        *,
        findings: list[IntelligenceFinding],
    ) -> float:
        """
        Reward genuinely independent intelligence dimensions.

        The bonus considers:

            - unique evidence records
            - unique relationships
            - unique entities
            - finding-family diversity

        The bonus is intentionally capped.

        This method is preserved from the previous model so
        downstream intelligence functionality remains available.
        """

        evidence_ids: set[int] = set()
        relationship_ids: set[int] = set()
        entity_ids: set[int] = set()
        finding_families: set[str] = set()

        for finding in findings:

            evidence_ids.update(
                self._safe_ids(
                    finding.supporting_evidence_ids
                )
            )

            relationship_ids.update(
                self._safe_ids(
                    finding.supporting_relationship_ids
                )
            )

            entity_ids.update(
                self._safe_ids(
                    finding.supporting_entity_ids
                )
            )

            finding_families.add(
                self._finding_family(
                    finding.title
                )
            )

        bonus = 0.0

        if len(evidence_ids) >= 2:
            bonus += self.EVIDENCE_BONUS

        if len(relationship_ids) >= 2:
            bonus += self.RELATIONSHIP_BONUS

        if len(entity_ids) >= 3:
            bonus += self.ENTITY_BONUS

        if len(finding_families) >= 3:
            bonus += self.FAMILY_BONUS

        if len(finding_families) >= 5:
            bonus += self.FAMILY_BONUS

        return min(
            bonus,
            self.MAX_INDEPENDENT_BONUS,
        )

    # ========================================================
    # FINDING FAMILY
    # ========================================================

    def _finding_family(
        self,
        title: str,
    ) -> str:
        """
        Group findings into broad reasoning families.

        This is intentionally deterministic and simple.
        """

        normalized = (
            title
            .strip()
            .lower()
        )

        family_keywords = {
            "relationship": (
                "relationship",
                "contact",
                "uses",
                "communication",
            ),
            "centrality": (
                "central",
                "hub",
                "articulation",
                "bridge",
                "activity",
            ),
            "cluster": (
                "cluster",
                "component",
                "network",
            ),
            "path": (
                "path",
                "multi-hop",
                "indirect",
            ),
            "evidence": (
                "evidence",
                "corroboration",
                "reinforcement",
            ),
            "convergence": (
                "convergence",
                "convergent",
                "compound",
            ),
        }

        for family, keywords in family_keywords.items():

            if any(
                keyword in normalized
                for keyword in keywords
            ):
                return family

        return "other"

    # ========================================================
    # AVERAGE CONFIDENCE
    # ========================================================

    def _average_confidence(
        self,
        findings: Iterable[IntelligenceFinding],
    ) -> float:
        """
        Calculate average finding confidence.

        Kept as a utility for future calibration stages.
        """

        values = [
            min(
                max(
                    float(
                        finding.confidence
                    ),
                    0.0,
                ),
                1.0,
            )
            for finding in findings
        ]

        if not values:
            return 0.0

        return (
            sum(values)
            / len(values)
        )

    # ========================================================
    # SEVERITY WEIGHT
    # ========================================================

    def _severity_weight(
        self,
        severity: IntelligenceSeverity,
    ) -> float:
        """
        Convert finding severity into a numerical weight.
        """

        return self.SEVERITY_WEIGHTS.get(
            severity,
            0.25,
        )

    # ========================================================
    # SCORE → SEVERITY
    # ========================================================

    def _score_to_severity(
        self,
        score: float,
    ) -> IntelligenceSeverity:
        """
        Convert numerical risk score into severity.

        Boundary contract:

            score > 0.90
                -> CRITICAL

            0.65 <= score <= 0.90
                -> HIGH

            0.35 <= score < 0.65
                -> MEDIUM

            score < 0.35
                -> LOW

        Therefore:

            0.900 -> HIGH
            0.901 -> CRITICAL
        """

        if score > 0.90:
            return IntelligenceSeverity.CRITICAL

        if score >= 0.65:
            return IntelligenceSeverity.HIGH

        if score >= 0.35:
            return IntelligenceSeverity.MEDIUM

        return IntelligenceSeverity.LOW

    # ========================================================
    # EXPLANATION
    # ========================================================

    def _build_explanation(
        self,
        *,
        findings: list[IntelligenceFinding],
        score: float,
        severity: IntelligenceSeverity,
    ) -> str:
        """
        Generate a human-readable risk explanation.

        The explanation reports the final calibrated score,
        rather than an intermediate severity-weighted value.
        """

        count = len(
            findings
        )

        unique_relationships = len(
            {
                relationship_id
                for finding in findings
                for relationship_id in self._safe_ids(
                    finding.supporting_relationship_ids
                )
            }
        )

        unique_evidence = len(
            {
                evidence_id
                for finding in findings
                for evidence_id in self._safe_ids(
                    finding.supporting_evidence_ids
                )
            }
        )

        unique_entities = len(
            {
                entity_id
                for finding in findings
                for entity_id in self._safe_ids(
                    finding.supporting_entity_ids
                )
            }
        )

        return (
            f"The intelligence analysis produced "
            f"{count} finding(s). "
            f"The calibrated risk score is "
            f"{score:.3f}, "
            f"corresponding to "
            f"{severity.value} severity. "
            f"The assessment considers "
            f"{unique_relationships} "
            f"unique relationship signal(s), "
            f"{unique_evidence} "
            f"unique evidence record(s), "
            f"and {unique_entities} "
            f"associated entit(ies), "
            f"with correlated derived findings "
            f"discounted to reduce risk inflation."
        )

    # ========================================================
    # VALID CONFIDENCE
    # ========================================================

    @staticmethod
    def _valid_confidence(
        confidence: float,
    ) -> bool:
        """
        Validate finding confidence.

        Confidence is normally constrained by the model layer,
        but the analyzer remains defensive.
        """

        try:
            value = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            return False

        return (
            0.0 <= value <= 1.0
            and value > 0.0
        )

    # ========================================================
    # UNIQUE FINDINGS
    # ========================================================

    @staticmethod
    def _unique_findings(
        findings: Iterable[IntelligenceFinding],
    ) -> list[IntelligenceFinding]:
        """
        Remove duplicate object references while preserving
        order.
        """

        result: list[
            IntelligenceFinding
        ] = []

        seen: set[int] = set()

        for finding in findings:

            identity = id(
                finding
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            result.append(
                finding
            )

        return result

    # ========================================================
    # SAFE IDS
    # ========================================================

    @staticmethod
    def _safe_ids(
        values: Iterable[int] | None,
    ) -> set[int]:
        """
        Safely normalize IDs into a set of integers.
        """

        if not values:
            return set()

        result: set[int] = set()

        for value in values:

            try:
                result.add(
                    int(
                        value
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return result


# ============================================================
# DEFAULT INSTANCE
# ============================================================

risk_analyzer = IntelligenceRiskAnalyzer()
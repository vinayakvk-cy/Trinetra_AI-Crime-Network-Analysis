from __future__ import annotations

from collections import Counter
from typing import Any

from app.ai.intelligence.models import (
    IntelligenceFinding,
    IntelligenceSeverity,
)


class IntelligenceAnalyzer:
    """
    Performs first-level intelligence analysis on structured
    investigation data.

    This class does not directly access the database.

    It receives structured investigation data and produces
    evidence-grounded intelligence findings.

    Responsibilities:

        1. Repeated relationships
        2. High-confidence relationships
        3. Highly connected entities
        4. Evidence-supported relationships
        5. Evidence-supported entity activity

    Higher-order graph reasoning is intentionally handled by
    IntelligenceReasoner rather than this class.
    """

    # ========================================================
    # MAIN ANALYSIS
    # ========================================================

    def analyze(
        self,
        *,
        entities: list[Any],
        evidence: list[Any],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Analyze structured investigation data.

        Original input objects are never modified.

        Returns:
            A list of first-level intelligence findings.
        """

        entities = list(entities or [])
        evidence = list(evidence or [])
        relationships = list(relationships or [])

        findings: list[IntelligenceFinding] = []

        # ----------------------------------------------------
        # 1. REPEATED RELATIONSHIPS
        # ----------------------------------------------------

        findings.extend(
            self._analyze_repeated_relationships(
                relationships=relationships,
            )
        )

        # ----------------------------------------------------
        # 2. HIGH-CONFIDENCE RELATIONSHIPS
        # ----------------------------------------------------

        findings.extend(
            self._analyze_high_confidence_relationships(
                relationships=relationships,
            )
        )

        # ----------------------------------------------------
        # 3. ENTITY CONNECTIONS
        # ----------------------------------------------------

        findings.extend(
            self._analyze_entity_connections(
                entities=entities,
                relationships=relationships,
            )
        )

        # ----------------------------------------------------
        # 4. EVIDENCE SUPPORT
        # ----------------------------------------------------

        findings.extend(
            self._analyze_evidence_support(
                evidence=evidence,
                relationships=relationships,
            )
        )

        # ----------------------------------------------------
        # 5. EVIDENCE-SUPPORTED ENTITY ACTIVITY
        # ----------------------------------------------------

        findings.extend(
            self._analyze_evidence_entity_activity(
                evidence=evidence,
                relationships=relationships,
            )
        )

        return findings

    # ========================================================
    # REPEATED RELATIONSHIPS
    # ========================================================

    def _analyze_repeated_relationships(
        self,
        *,
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Detect repeated relationship records between the same
        entities using the same relationship type.

        Example:

            Entity 1 -- contacted --> Entity 2
            Entity 1 -- contacted --> Entity 2
            Entity 1 -- contacted --> Entity 2

        Repeated observations increase confidence in an
        association but do not independently establish intent.
        """

        if not relationships:
            return []

        relationship_counter: Counter[
            tuple[int, int, str]
        ] = Counter()

        relationship_map: dict[
            tuple[int, int, str],
            list[int],
        ] = {}

        evidence_map: dict[
            tuple[int, int, str],
            list[int],
        ] = {}

        for relationship in relationships:

            source_id = self._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            )

            target_id = self._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            )

            relationship_type = self._relationship_type_value(
                relationship
            )

            if (
                source_id is None
                or target_id is None
                or relationship_type is None
            ):
                continue

            key = (
                source_id,
                target_id,
                relationship_type,
            )

            relationship_counter[key] += 1

            relationship_id = self._safe_int(
                getattr(
                    relationship,
                    "id",
                    None,
                )
            )

            if relationship_id is not None:

                relationship_map.setdefault(
                    key,
                    [],
                ).append(
                    relationship_id
                )

            relationship_evidence_ids = (
                self._extract_evidence_ids(
                    relationship
                )
            )

            if relationship_evidence_ids:

                evidence_map.setdefault(
                    key,
                    [],
                ).extend(
                    relationship_evidence_ids
                )

        findings: list[IntelligenceFinding] = []

        for key, count in relationship_counter.items():

            if count < 2:
                continue

            source_id, target_id, relationship_type = key

            relationship_ids = list(
                dict.fromkeys(
                    relationship_map.get(
                        key,
                        [],
                    )
                )
            )

            evidence_ids = list(
                dict.fromkeys(
                    evidence_map.get(
                        key,
                        [],
                    )
                )
            )

            confidence = min(
                0.60 + (count * 0.08),
                0.95,
            )

            # Evidence reinforcement slightly increases
            # confidence, but never beyond 0.95.
            if evidence_ids:
                confidence = min(
                    confidence + 0.03,
                    0.95,
                )

            findings.append(
                IntelligenceFinding(
                    title="Repeated relationship detected",
                    description=(
                        f"Entities {source_id} and {target_id} "
                        f"have {count} observed "
                        f"'{relationship_type}' relationship "
                        f"record(s)."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if count >= 5
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=evidence_ids,
                    supporting_relationship_ids=(
                        relationship_ids
                    ),
                )
            )

        return findings

    # ========================================================
    # HIGH-CONFIDENCE RELATIONSHIPS
    # ========================================================

    def _analyze_high_confidence_relationships(
        self,
        *,
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Identify individual relationships with high confidence.

        Threshold:
            confidence >= 0.80
        """

        if not relationships:
            return []

        findings: list[IntelligenceFinding] = []

        for relationship in relationships:

            confidence = self._safe_float(
                getattr(
                    relationship,
                    "confidence",
                    None,
                )
            )

            if confidence is None:
                continue

            if confidence < 0.80:
                continue

            source_id = self._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            )

            target_id = self._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            )

            relationship_type = self._relationship_type_value(
                relationship
            )

            relationship_id = self._safe_int(
                getattr(
                    relationship,
                    "id",
                    None,
                )
            )

            if (
                source_id is None
                or target_id is None
                or relationship_type is None
            ):
                continue

            evidence_ids = (
                self._extract_evidence_ids(
                    relationship
                )
            )

            severity = (
                IntelligenceSeverity.HIGH
                if confidence >= 0.90
                else IntelligenceSeverity.MEDIUM
            )

            findings.append(
                IntelligenceFinding(
                    title="High-confidence relationship",
                    description=(
                        f"A high-confidence "
                        f"'{relationship_type}' relationship "
                        f"exists between entities "
                        f"{source_id} and {target_id}."
                    ),
                    severity=severity,
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=evidence_ids,
                    supporting_relationship_ids=(
                        [relationship_id]
                        if relationship_id is not None
                        else []
                    ),
                )
            )

        return findings

    # ========================================================
    # ENTITY CONNECTIONS
    # ========================================================

    def _analyze_entity_connections(
        self,
        *,
        entities: list[Any],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Detect highly connected entities.

        Connection count measures relationship records rather
        than unique neighbors.

        This is deliberately conservative because high
        connectivity alone does not imply malicious activity.
        """

        if not relationships:
            return []

        findings: list[IntelligenceFinding] = []

        connection_counter: Counter[int] = Counter()

        connected_entities: dict[
            int,
            set[int],
        ] = {}

        relationship_ids_by_entity: dict[
            int,
            list[int],
        ] = {}

        evidence_ids_by_entity: dict[
            int,
            list[int],
        ] = {}

        valid_entity_ids = {
            self._safe_int(
                getattr(
                    entity,
                    "id",
                    None,
                )
            )
            for entity in entities
        }

        valid_entity_ids.discard(None)

        for relationship in relationships:

            source_id = self._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            )

            target_id = self._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            )

            if (
                source_id is None
                or target_id is None
            ):
                continue

            connection_counter[source_id] += 1
            connection_counter[target_id] += 1

            connected_entities.setdefault(
                source_id,
                set(),
            ).add(
                target_id
            )

            connected_entities.setdefault(
                target_id,
                set(),
            ).add(
                source_id
            )

            relationship_id = self._safe_int(
                getattr(
                    relationship,
                    "id",
                    None,
                )
            )

            evidence_ids = (
                self._extract_evidence_ids(
                    relationship
                )
            )

            for entity_id in (
                source_id,
                target_id,
            ):

                if relationship_id is not None:

                    relationship_ids_by_entity.setdefault(
                        entity_id,
                        [],
                    ).append(
                        relationship_id
                    )

                if evidence_ids:

                    evidence_ids_by_entity.setdefault(
                        entity_id,
                        [],
                    ).extend(
                        evidence_ids
                    )

        for entity_id, connection_count in (
            connection_counter.items()
        ):

            if connection_count < 3:
                continue

            related_ids = sorted(
                connected_entities.get(
                    entity_id,
                    set(),
                )
            )

            confidence = min(
                0.55 + (connection_count * 0.05),
                0.90,
            )

            relationship_ids = list(
                dict.fromkeys(
                    relationship_ids_by_entity.get(
                        entity_id,
                        [],
                    )
                )
            )

            evidence_ids = list(
                dict.fromkeys(
                    evidence_ids_by_entity.get(
                        entity_id,
                        [],
                    )
                )
            )

            findings.append(
                IntelligenceFinding(
                    title="Highly connected entity",
                    description=(
                        f"Entity {entity_id} participates in "
                        f"{connection_count} relationship "
                        f"record(s) involving "
                        f"{len(related_ids)} unique connected "
                        f"entity/entities. This may indicate "
                        f"an important network position."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if connection_count >= 5
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id,
                        *related_ids,
                    ],
                    supporting_evidence_ids=(
                        evidence_ids
                    ),
                    supporting_relationship_ids=(
                        relationship_ids
                    ),
                )
            )

        return findings

    # ========================================================
    # EVIDENCE SUPPORT
    # ========================================================

    def _analyze_evidence_support(
        self,
        *,
        evidence: list[Any],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Identify relationships explicitly associated with
        evidence records.

        Supported relationship attributes include:

            evidence_id
            evidence_ids
            supporting_evidence_id
            supporting_evidence_ids

        The method only reports evidence IDs that actually
        exist in the supplied evidence collection.
        """

        if not evidence or not relationships:
            return []

        evidence_ids = {
            self._safe_int(
                getattr(
                    item,
                    "id",
                    None,
                )
            )
            for item in evidence
        }

        evidence_ids.discard(None)

        if not evidence_ids:
            return []

        findings: list[IntelligenceFinding] = []

        for relationship in relationships:

            source_id = self._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            )

            target_id = self._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            )

            relationship_id = self._safe_int(
                getattr(
                    relationship,
                    "id",
                    None,
                )
            )

            if (
                source_id is None
                or target_id is None
            ):
                continue

            relationship_evidence_ids = [
                evidence_id
                for evidence_id
                in self._extract_evidence_ids(
                    relationship
                )
                if evidence_id in evidence_ids
            ]

            if not relationship_evidence_ids:
                continue

            relationship_type = (
                self._relationship_type_value(
                    relationship
                )
            )

            if relationship_type is None:
                relationship_type = "relationship"

            confidence = 0.75

            relationship_confidence = (
                self._safe_float(
                    getattr(
                        relationship,
                        "confidence",
                        None,
                    )
                )
            )

            # Evidence-backed relationships can inherit a
            # limited amount of confidence from the underlying
            # relationship, while remaining conservative.
            if relationship_confidence is not None:
                confidence = min(
                    max(
                        0.75,
                        relationship_confidence,
                    ),
                    0.90,
                )

            findings.append(
                IntelligenceFinding(
                    title="Relationship supported by evidence",
                    description=(
                        f"The observed "
                        f"'{relationship_type}' relationship "
                        f"between entities {source_id} and "
                        f"{target_id} is associated with "
                        f"{len(relationship_evidence_ids)} "
                        f"evidence record(s): "
                        f"{', '.join(map(str, relationship_evidence_ids))}."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if confidence >= 0.90
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        source_id,
                        target_id,
                    ],
                    supporting_evidence_ids=(
                        relationship_evidence_ids
                    ),
                    supporting_relationship_ids=(
                        [relationship_id]
                        if relationship_id is not None
                        else []
                    ),
                )
            )

        return findings

    # ========================================================
    # EVIDENCE-SUPPORTED ENTITY ACTIVITY
    # ========================================================

    def _analyze_evidence_entity_activity(
        self,
        *,
        evidence: list[Any],
        relationships: list[Any],
    ) -> list[IntelligenceFinding]:
        """
        Detect entities whose observed relationships are
        explicitly supported by evidence.

        This creates a useful bridge between:

            Evidence
                ↓
            Relationship
                ↓
            Entity

        It does not infer evidence where no explicit reference
        exists.
        """

        if not evidence or not relationships:
            return []

        valid_evidence_ids = {
            self._safe_int(
                getattr(
                    item,
                    "id",
                    None,
                )
            )
            for item in evidence
        }

        valid_evidence_ids.discard(None)

        if not valid_evidence_ids:
            return []

        entity_evidence: dict[
            int,
            set[int],
        ] = {}

        entity_relationships: dict[
            int,
            set[int],
        ] = {}

        for relationship in relationships:

            source_id = self._safe_int(
                getattr(
                    relationship,
                    "source_entity_id",
                    None,
                )
            )

            target_id = self._safe_int(
                getattr(
                    relationship,
                    "target_entity_id",
                    None,
                )
            )

            if (
                source_id is None
                or target_id is None
            ):
                continue

            evidence_ids = {
                evidence_id
                for evidence_id
                in self._extract_evidence_ids(
                    relationship
                )
                if evidence_id in valid_evidence_ids
            }

            if not evidence_ids:
                continue

            relationship_id = self._safe_int(
                getattr(
                    relationship,
                    "id",
                    None,
                )
            )

            for entity_id in (
                source_id,
                target_id,
            ):

                entity_evidence.setdefault(
                    entity_id,
                    set(),
                ).update(
                    evidence_ids
                )

                if relationship_id is not None:

                    entity_relationships.setdefault(
                        entity_id,
                        set(),
                    ).add(
                        relationship_id
                    )

        findings: list[IntelligenceFinding] = []

        for entity_id, evidence_id_set in (
            entity_evidence.items()
        ):

            relationship_id_set = (
                entity_relationships.get(
                    entity_id,
                    set(),
                )
            )

            if not evidence_id_set:
                continue

            evidence_count = len(
                evidence_id_set
            )

            relationship_count = len(
                relationship_id_set
            )

            confidence = min(
                0.68
                + (
                    min(
                        evidence_count,
                        4,
                    )
                    * 0.05
                )
                + (
                    min(
                        relationship_count,
                        4,
                    )
                    * 0.03
                ),
                0.90,
            )

            findings.append(
                IntelligenceFinding(
                    title="Evidence-supported entity activity",
                    description=(
                        f"Entity {entity_id} is associated "
                        f"with {relationship_count} observed "
                        f"relationship record(s) supported by "
                        f"{evidence_count} distinct evidence "
                        f"record(s). This provides explicit "
                        f"evidence linkage for the observed "
                        f"entity activity."
                    ),
                    severity=(
                        IntelligenceSeverity.HIGH
                        if confidence >= 0.85
                        else IntelligenceSeverity.MEDIUM
                    ),
                    confidence=round(
                        confidence,
                        3,
                    ),
                    supporting_entity_ids=[
                        entity_id
                    ],
                    supporting_evidence_ids=sorted(
                        evidence_id_set
                    ),
                    supporting_relationship_ids=sorted(
                        relationship_id_set
                    ),
                )
            )

        return findings

    # ========================================================
    # RELATIONSHIP TYPE HELPER
    # ========================================================

    @staticmethod
    def _relationship_type_value(
        relationship: Any,
    ) -> str | None:
        """
        Safely normalize a relationship type.

        Supports both:

            relationship_type="contacted"

        and:

            relationship_type=RelationshipType.CONTACTED
        """

        relationship_type = getattr(
            relationship,
            "relationship_type",
            None,
        )

        if relationship_type is None:
            return None

        value = getattr(
            relationship_type,
            "value",
            relationship_type,
        )

        if value is None:
            return None

        return str(value)

    # ========================================================
    # EVIDENCE ID EXTRACTION
    # ========================================================

    @classmethod
    def _extract_evidence_ids(
        cls,
        relationship: Any,
    ) -> list[int]:
        """
        Extract explicitly associated evidence IDs.

        Several attribute names are supported so this analyzer
        remains compatible while the investigation data model
        evolves.

        Supported:

            evidence_id
            evidence_ids
            supporting_evidence_id
            supporting_evidence_ids
        """

        candidate_attributes = (
            "evidence_id",
            "evidence_ids",
            "supporting_evidence_id",
            "supporting_evidence_ids",
        )

        extracted: list[int] = []

        for attribute_name in candidate_attributes:

            value = getattr(
                relationship,
                attribute_name,
                None,
            )

            if value is None:
                continue

            if isinstance(
                value,
                (list, tuple, set),
            ):

                values = value

            else:

                values = [value]

            for item in values:

                evidence_id = cls._safe_int(
                    item
                )

                if evidence_id is not None:
                    extracted.append(
                        evidence_id
                    )

        return list(
            dict.fromkeys(
                extracted
            )
        )

    # ========================================================
    # SAFE FLOAT
    # ========================================================

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float | None:
        """
        Safely convert a value to float.
        """

        if value is None:
            return None

        try:

            converted = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if converted < 0.0:
            return 0.0

        if converted > 1.0:
            return 1.0

        return converted

    # ========================================================
    # SAFE INTEGER
    # ========================================================

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> int | None:
        """
        Safely convert a value to integer.
        """

        if value is None:
            return None

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return None


# ============================================================
# DEFAULT ANALYZER
# ============================================================

intelligence_analyzer = IntelligenceAnalyzer()
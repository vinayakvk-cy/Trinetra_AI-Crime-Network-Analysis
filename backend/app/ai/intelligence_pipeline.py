from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.entity_extraction import entity_extractor
from app.ai.relationship_extractor import relationship_extractor


# ============================================================
# EXTRACTED INTELLIGENCE
# ============================================================


@dataclass
class ExtractedIntelligence:
    """
    Intermediate result produced by the raw intelligence pipeline.

    This represents structured information extracted from raw
    intelligence before it is passed to the deeper intelligence
    analysis engine.

    Flow:

        Raw Intelligence
              ↓
        Entity Extraction
              ↓
        Relationship Extraction
              ↓
        ExtractedIntelligence
              ↓
        IntelligenceEngine
    """

    source_text: str

    entities: list[dict[str, Any]] = field(
        default_factory=list
    )

    relationships: list[dict[str, Any]] = field(
        default_factory=list
    )

    insights: list[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# INTELLIGENCE PIPELINE
# ============================================================


class IntelligencePipeline:
    """
    Central orchestration layer for TRINETRA AI intelligence.

    Converts raw intelligence text into structured intelligence.

    Flow:

        Raw Intelligence
              ↓
        Text Processing
              ↓
        Entity Extraction
              ↓
        Relationship Extraction
              ↓
        Initial Insights
              ↓
        Confidence Calculation
              ↓
        ExtractedIntelligence
    """

    def __init__(self) -> None:
        self.pipeline_name = (
            "TRINETRA Intelligence Pipeline"
        )

        self.version = "1.0.0"

    # ========================================================
    # PROCESS INTELLIGENCE
    # ========================================================

    def process(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractedIntelligence:
        """
        Process raw intelligence text.

        Steps:

            1. Validate input
            2. Perform basic text analysis
            3. Extract entities
            4. Extract relationships
            5. Generate initial insights
            6. Calculate confidence
            7. Return structured intelligence
        """

        # ----------------------------------------------------
        # VALIDATE INPUT
        # ----------------------------------------------------

        if not isinstance(text, str):
            raise TypeError(
                "Intelligence input must be a string."
            )

        text = text.strip()

        if not text:
            raise ValueError(
                "Intelligence input cannot be empty."
            )

        # ----------------------------------------------------
        # CREATE RESULT
        # ----------------------------------------------------

        result = ExtractedIntelligence(
            source_text=text,
            metadata=dict(metadata or {}),
        )

        # ----------------------------------------------------
        # STEP 1: BASIC TEXT ANALYSIS
        # ----------------------------------------------------

        result.metadata["pipeline_name"] = (
            self.pipeline_name
        )

        result.metadata["pipeline_version"] = (
            self.version
        )

        result.metadata["text_length"] = len(text)

        result.metadata["word_count"] = len(
            text.split()
        )

        # ----------------------------------------------------
        # STEP 2: ENTITY EXTRACTION
        # ----------------------------------------------------

        result.entities = self.extract_entities(
            text=text,
        )

        # ----------------------------------------------------
        # STEP 3: RELATIONSHIP EXTRACTION
        # ----------------------------------------------------

        result.relationships = (
            self.extract_relationships(
                text=text,
                entities=result.entities,
            )
        )

        # ----------------------------------------------------
        # STEP 4: INITIAL INSIGHTS
        # ----------------------------------------------------

        result.insights = self.generate_insights(
            result=result,
        )

        # ----------------------------------------------------
        # STEP 5: CONFIDENCE
        # ----------------------------------------------------

        result.confidence = (
            self.calculate_confidence(
                result=result,
            )
        )

        # ----------------------------------------------------
        # STEP 6: STORE COUNTS IN METADATA
        # ----------------------------------------------------

        result.metadata["entity_count"] = len(
            result.entities
        )

        result.metadata["relationship_count"] = len(
            result.relationships
        )

        result.metadata["insight_count"] = len(
            result.insights
        )

        return result

    # ========================================================
    # ENTITY EXTRACTION
    # ========================================================

    def extract_entities(
        self,
        *,
        text: str,
    ) -> list[dict[str, Any]]:
        """
        Extract entities from raw intelligence text.

        Converts extractor-specific entity objects into
        dictionaries so the rest of the intelligence pipeline
        remains independent from the extraction implementation.
        """

        extracted = entity_extractor.extract(
            text
        )

        entities: list[dict[str, Any]] = []

        for entity in extracted:

            entity_type = getattr(
                entity.entity_type,
                "value",
                str(entity.entity_type),
            )

            entities.append(
                {
                    "entity_type": entity_type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "start_position": (
                        entity.start_position
                    ),
                    "end_position": (
                        entity.end_position
                    ),
                    "source": entity.source,
                }
            )

        return entities

    # ========================================================
    # RELATIONSHIP EXTRACTION
    # ========================================================

    def extract_relationships(
        self,
        *,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Automatically extract relationships between
        detected entities.

        The relationship extractor is deliberately kept
        separate from the pipeline so it can later be
        replaced or enhanced with:

            - NLP models
            - Machine learning
            - Transformer models
            - LLM reasoning
            - Graph-based inference
        """

        if not entities:
            return []

        extracted = relationship_extractor.extract(
            text=text,
            entities=entities,
        )

        relationships: list[dict[str, Any]] = []

        for relationship in extracted:

            # ------------------------------------------------
            # relationship_extractor currently returns
            # dictionaries.
            # ------------------------------------------------

            if isinstance(
                relationship,
                dict,
            ):

                relationships.append(
                    {
                        "source_entity": (
                            relationship.get(
                                "source_entity"
                            )
                        ),
                        "target_entity": (
                            relationship.get(
                                "target_entity"
                            )
                        ),
                        "relationship_type": (
                            relationship.get(
                                "relationship_type"
                            )
                        ),
                        "confidence": (
                            relationship.get(
                                "confidence",
                                0.0,
                            )
                        ),
                        "evidence_text": (
                            relationship.get(
                                "evidence_text",
                                "",
                            )
                        ),
                        "source": (
                            relationship.get(
                                "source",
                                "relationship_extraction",
                            )
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # Defensive support for dataclass/object output.
            # ------------------------------------------------

            relationship_type = getattr(
                relationship.relationship_type,
                "value",
                str(
                    relationship.relationship_type
                ),
            )

            relationships.append(
                {
                    "source_entity": (
                        relationship.source_entity
                    ),
                    "target_entity": (
                        relationship.target_entity
                    ),
                    "relationship_type": (
                        relationship_type
                    ),
                    "confidence": (
                        relationship.confidence
                    ),
                    "evidence_text": getattr(
                        relationship,
                        "evidence_text",
                        "",
                    ),
                    "source": getattr(
                        relationship,
                        "source",
                        "relationship_extraction",
                    ),
                }
            )

        return relationships

    # ========================================================
    # INSIGHT GENERATION
    # ========================================================

    def generate_insights(
        self,
        *,
        result: ExtractedIntelligence,
    ) -> list[str]:
        """
        Generate initial intelligence observations.

        These are lightweight observations.

        The deeper IntelligenceEngine is responsible for:

            - Investigation-level analysis
            - Pattern detection
            - Risk assessment
            - Intelligence findings
            - Cross-evidence reasoning
        """

        insights: list[str] = []

        # ----------------------------------------------------
        # ENTITY INSIGHT
        # ----------------------------------------------------

        if result.entities:

            insights.append(
                f"Detected "
                f"{len(result.entities)} "
                f"entity/entities."
            )

        # ----------------------------------------------------
        # RELATIONSHIP INSIGHT
        # ----------------------------------------------------

        if result.relationships:

            insights.append(
                f"Detected "
                f"{len(result.relationships)} "
                f"relationship(s) between entities."
            )

        # ----------------------------------------------------
        # ENTITY + RELATIONSHIP INSIGHT
        # ----------------------------------------------------

        if (
            result.entities
            and result.relationships
        ):

            insights.append(
                "Structured connections were identified "
                "between extracted entities."
            )

        # ----------------------------------------------------
        # NO STRUCTURED DATA
        # ----------------------------------------------------

        if (
            not result.entities
            and not result.relationships
        ):

            insights.append(
                "No structured intelligence "
                "was detected in the provided text."
            )

        return insights

    # ========================================================
    # CONFIDENCE CALCULATION
    # ========================================================

    def calculate_confidence(
        self,
        *,
        result: ExtractedIntelligence,
    ) -> float:
        """
        Calculate an initial pipeline confidence score.

        Current weighting:

            Source text       → 0.20
            Entities          → 0.40
            Relationships     → 0.40

        This is intentionally a foundation.

        Future versions can incorporate:

            - Entity confidence
            - Relationship confidence
            - NLP model confidence
            - Source reliability
            - Evidence strength
            - Cross-source verification
            - Temporal consistency
            - Graph consistency
        """

        confidence = 0.0

        # ----------------------------------------------------
        # SOURCE TEXT
        # ----------------------------------------------------

        if result.source_text:

            confidence += 0.20

        # ----------------------------------------------------
        # ENTITY CONFIDENCE
        # ----------------------------------------------------

        if result.entities:

            entity_confidences = [
                float(
                    entity.get(
                        "confidence",
                        0.0,
                    )
                )
                for entity in result.entities
            ]

            if entity_confidences:

                average_entity_confidence = (
                    sum(entity_confidences)
                    / len(entity_confidences)
                )

                confidence += (
                    0.40
                    * average_entity_confidence
                )

        # ----------------------------------------------------
        # RELATIONSHIP CONFIDENCE
        # ----------------------------------------------------

        if result.relationships:

            relationship_confidences = [
                float(
                    relationship.get(
                        "confidence",
                        0.0,
                    )
                )
                for relationship in result.relationships
            ]

            if relationship_confidences:

                average_relationship_confidence = (
                    sum(relationship_confidences)
                    / len(
                        relationship_confidences
                    )
                )

                confidence += (
                    0.40
                    * average_relationship_confidence
                )

        return round(
            min(
                max(
                    confidence,
                    0.0,
                ),
                1.0,
            ),
            3,
        )


# ============================================================
# DEFAULT PIPELINE INSTANCE
# ============================================================


intelligence_pipeline = IntelligencePipeline()
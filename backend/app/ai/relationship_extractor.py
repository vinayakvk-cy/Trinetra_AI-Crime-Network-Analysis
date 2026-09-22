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
    Structured result produced from raw intelligence.

    Flow:

        Raw Intelligence
              ↓
        Entity Extraction
              ↓
        Relationship Extraction
              ↓
        Initial Insights
              ↓
        Confidence
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
    """

    def __init__(self) -> None:

        self.pipeline_name = (
            "TRINETRA Intelligence Pipeline"
        )

        self.version = "1.0.0"

    # ========================================================
    # PROCESS
    # ========================================================

    def process(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractedIntelligence:
        """
        Process raw intelligence.
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
        # PIPELINE METADATA
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
        # ENTITY EXTRACTION
        # ----------------------------------------------------

        result.entities = self.extract_entities(
            text
        )

        # ----------------------------------------------------
        # RELATIONSHIP EXTRACTION
        # ----------------------------------------------------

        result.relationships = (
            self.extract_relationships(
                text=text,
                entities=result.entities,
            )
        )

        # ----------------------------------------------------
        # INSIGHTS
        # ----------------------------------------------------

        result.insights = self.generate_insights(
            result
        )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        result.confidence = (
            self.calculate_confidence(result)
        )

        return result

    # ========================================================
    # ENTITY EXTRACTION
    # ========================================================

    def extract_entities(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """
        Extract entities from raw intelligence.
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
        Extract relationships between entities.

        IMPORTANT:

        relationship_extractor.extract()
        already returns dictionaries.

        Therefore we preserve those dictionaries here
        instead of treating them as dataclass objects.
        """

        if not entities:
            return []

        relationships = (
            relationship_extractor.extract(
                text=text,
                entities=entities,
            )
        )

        normalized: list[dict[str, Any]] = []

        for relationship in relationships:

            if not isinstance(
                relationship,
                dict,
            ):
                continue

            normalized.append(
                {
                    "source_entity": relationship.get(
                        "source_entity"
                    ),
                    "target_entity": relationship.get(
                        "target_entity"
                    ),
                    "relationship_type": relationship.get(
                        "relationship_type"
                    ),
                    "confidence": relationship.get(
                        "confidence",
                        0.0,
                    ),
                    "evidence_text": relationship.get(
                        "evidence_text",
                        "",
                    ),
                    "source": relationship.get(
                        "source",
                        "relationship_extraction",
                    ),
                }
            )

        return normalized

    # ========================================================
    # INSIGHT GENERATION
    # ========================================================

    def generate_insights(
        self,
        result: ExtractedIntelligence,
    ) -> list[str]:
        """
        Generate initial intelligence observations.
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
        # RELATIONSHIP DETAILS
        # ----------------------------------------------------

        relationship_types = sorted(
            {
                str(
                    relationship.get(
                        "relationship_type"
                    )
                )
                for relationship in result.relationships
                if relationship.get(
                    "relationship_type"
                )
            }
        )

        if relationship_types:

            insights.append(
                "Relationship types detected: "
                + ", ".join(
                    relationship_types
                )
                + "."
            )

        # ----------------------------------------------------
        # NO STRUCTURED INTELLIGENCE
        # ----------------------------------------------------

        if not result.entities and not result.relationships:

            insights.append(
                "No structured intelligence "
                "was detected in the provided text."
            )

        return insights

    # ========================================================
    # CONFIDENCE
    # ========================================================

    def calculate_confidence(
        self,
        result: ExtractedIntelligence,
    ) -> float:
        """
        Calculate an initial pipeline confidence score.

        Current foundation:

            Source text       = 0.20
            Entities          = 0.40
            Relationships     = 0.40
        """

        confidence = 0.0

        # ----------------------------------------------------
        # SOURCE
        # ----------------------------------------------------

        if result.source_text:

            confidence += 0.20

        # ----------------------------------------------------
        # ENTITIES
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
        # RELATIONSHIPS
        # ----------------------------------------------------

        if result.relationships:

            relationship_confidences = [
                float(
                    relationship.get(
                        "confidence",
                        0.0,
                    )
                )
                for relationship
                in result.relationships
            ]

            if relationship_confidences:

                average_relationship_confidence = (
                    sum(
                        relationship_confidences
                    )
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
                max(confidence, 0.0),
                1.0,
            ),
            3,
        )


# ============================================================
# DEFAULT PIPELINE INSTANCE
# ============================================================


intelligence_pipeline = IntelligencePipeline()
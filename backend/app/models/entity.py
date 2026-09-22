from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# ENTITY TYPE
# ============================================================


class EntityType(str, Enum):
    """
    Supported entity types within TRINETRA.
    """

    PERSON = "person"
    PHONE = "phone"
    EMAIL = "email"
    VEHICLE = "vehicle"
    LOCATION = "location"
    ADDRESS = "address"
    ORGANIZATION = "organization"
    SOCIAL_ACCOUNT = "social_account"
    BANK_ACCOUNT = "bank_account"
    TRANSACTION = "transaction"
    DEVICE = "device"
    CASE = "case"
    EVIDENCE = "evidence"
    UNKNOWN = "unknown"


# ============================================================
# ENTITY SOURCE
# ============================================================


class EntitySource(str, Enum):
    """
    Primary source from which an entity was obtained.
    """

    FIR = "fir"
    CDR = "cdr"
    TRANSACTION = "transaction"
    VEHICLE = "vehicle"
    GPS = "gps"
    SOCIAL_MEDIA = "social_media"
    JAIL_RECORD = "jail_record"
    FORENSIC = "forensic"
    POSTMORTEM = "postmortem"
    MANUAL = "manual"
    NLP = "nlp"
    UNKNOWN = "unknown"


# ============================================================
# ENTITY MODEL
# ============================================================


class Entity(FullBaseModel):
    """
    Central entity model for TRINETRA.

    An entity represents a real-world or analytical object
    extracted from one or more source records.

    Relationships between entities are handled by Neo4j.
    """

    __tablename__ = "entities"

    # ========================================================
    # ENTITY IDENTIFICATION
    # ========================================================

    entity_type: Mapped[EntityType] = mapped_column(
        SQLEnum(
            EntityType,
            name="entitytype",
            values_callable=lambda enum: [
                member.value for member in enum
            ],
        ),
        default=EntityType.UNKNOWN,
        nullable=False,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    normalized_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    # ========================================================
    # EXTERNAL / SOURCE IDENTIFIER
    # ========================================================

    external_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    source: Mapped[EntitySource] = mapped_column(
        SQLEnum(
            EntitySource,
            name="entitysource",
            values_callable=lambda enum: [
                member.value for member in enum
            ],
        ),
        default=EntitySource.UNKNOWN,
        nullable=False,
        index=True,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ========================================================
    # ENTITY DESCRIPTION
    # ========================================================

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # NLP INFORMATION
    # ========================================================

    extraction_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    extraction_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    linking_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # GRAPH INFORMATION
    # ========================================================

    graph_node_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    # ========================================================
    # ANALYTICAL INFORMATION
    # ========================================================

    risk_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ========================================================
    # ENTITY METHODS
    # ========================================================

    def set_extraction_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set NLP extraction confidence.

        Expected range:

            0.0 -> 1.0
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Extraction confidence must be between 0.0 and 1.0."
            )

        self.extraction_confidence = confidence

    def set_linking_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set entity-linking confidence.

        Expected range:

            0.0 -> 1.0
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Linking confidence must be between 0.0 and 1.0."
            )

        self.linking_confidence = confidence

    def set_risk_score(
        self,
        score: int,
    ) -> None:
        """
        Set analytical risk score.

        Expected range:

            0 -> 100
        """

        if not 0 <= score <= 100:
            raise ValueError(
                "Risk score must be between 0 and 100."
            )

        self.risk_score = score

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<Entity("
            f"id={self.id}, "
            f"type='{self.entity_type.value}', "
            f"name='{self.name}', "
            f"source='{self.source.value}'"
            f")>"
        )
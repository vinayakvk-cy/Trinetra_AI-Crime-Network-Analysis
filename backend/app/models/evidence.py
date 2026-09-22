from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import FullBaseModel


# ============================================================
# EVIDENCE TYPE
# ============================================================


class EvidenceType(str, Enum):
    """
    Type/category of evidence.
    """

    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FIR = "fir"
    CDR = "cdr"
    TRANSACTION = "transaction"
    GPS = "gps"
    VEHICLE = "vehicle"
    SOCIAL_MEDIA = "social_media"
    JAIL_RECORD = "jail_record"
    FORENSIC = "forensic"
    POSTMORTEM = "postmortem"
    DIGITAL = "digital"
    PHYSICAL = "physical"
    TESTIMONY = "testimony"
    OTHER = "other"


# ============================================================
# EVIDENCE STATUS
# ============================================================


class EvidenceStatus(str, Enum):
    """
    Current processing state of evidence.
    """

    RECEIVED = "received"
    PENDING_REVIEW = "pending_review"
    UNDER_ANALYSIS = "under_analysis"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ============================================================
# EVIDENCE MODEL
# ============================================================


class Evidence(FullBaseModel):
    """
    Evidence record associated with a TRINETRA case.
    """

    __tablename__ = "evidence"

    # ========================================================
    # CASE REFERENCE
    # ========================================================

    case_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ========================================================
    # IDENTIFICATION
    # ========================================================

    evidence_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # TYPE / STATUS
    # ========================================================

    evidence_type: Mapped[EvidenceType] = mapped_column(
        SQLEnum(EvidenceType),
        default=EvidenceType.OTHER,
        nullable=False,
        index=True,
    )

    status: Mapped[EvidenceStatus] = mapped_column(
        SQLEnum(EvidenceStatus),
        default=EvidenceStatus.RECEIVED,
        nullable=False,
        index=True,
    )

    # ========================================================
    # SOURCE INFORMATION
    # ========================================================

    source_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_file: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ========================================================
    # FILE INFORMATION
    # ========================================================

    file_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    file_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    file_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ========================================================
    # NLP / EXTRACTION
    # ========================================================

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # FORENSIC INFORMATION
    # ========================================================

    forensic_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    forensic_confidence: Mapped[float | None] = mapped_column(
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
    # STATUS METHODS
    # ========================================================

    def mark_pending_review(self) -> None:
        self.status = EvidenceStatus.PENDING_REVIEW

    def start_analysis(self) -> None:
        self.status = EvidenceStatus.UNDER_ANALYSIS

    def mark_verified(self) -> None:
        self.status = EvidenceStatus.VERIFIED

    def mark_disputed(self) -> None:
        self.status = EvidenceStatus.DISPUTED

    def mark_rejected(self) -> None:
        self.status = EvidenceStatus.REJECTED

    def archive(self) -> None:
        self.status = EvidenceStatus.ARCHIVED

    # ========================================================
    # CONFIDENCE METHODS
    # ========================================================

    def set_extraction_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set NLP extraction confidence.

        Range: 0.0 - 1.0
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Extraction confidence must be between 0.0 and 1.0."
            )

        self.extraction_confidence = confidence

    def set_forensic_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set forensic analysis confidence.

        Range: 0.0 - 1.0
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Forensic confidence must be between 0.0 and 1.0."
            )

        self.forensic_confidence = confidence

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<Evidence("
            f"id={self.id}, "
            f"evidence_number='{self.evidence_number}', "
            f"type='{self.evidence_type.value}', "
            f"status='{self.status.value}'"
            f")>"
        )
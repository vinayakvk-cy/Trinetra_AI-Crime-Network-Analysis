from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.investigation_evidence import (
    InvestigationEvidence,
    InvestigationEvidenceRelation,
)
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# SCHEMAS
# ============================================================


class InvestigationEvidenceCreate(BaseModel):
    """
    Request schema for linking evidence to an investigation.
    """

    investigation_id: int = Field(
        ...,
        gt=0,
        description="ID of the investigation",
    )

    evidence_id: int = Field(
        ...,
        gt=0,
        description="ID of the evidence",
    )

    relation: InvestigationEvidenceRelation = Field(
        default=InvestigationEvidenceRelation.RELEVANT,
        description="Relationship between investigation and evidence",
    )

    notes: str | None = Field(
        default=None,
        description="Additional notes about the relationship",
    )


class InvestigationEvidenceUpdate(BaseModel):
    """
    Request schema for updating an investigation-evidence link.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    relation: InvestigationEvidenceRelation | None = None

    notes: str | None = None


class InvestigationEvidenceResponse(BaseModel):
    """
    Response returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    investigation_id: int
    evidence_id: int
    relation: InvestigationEvidenceRelation
    notes: str | None

    created_at: object
    updated_at: object


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/investigation-evidence",
    tags=["Investigation Evidence"],
)


# ============================================================
# CREATE LINK
# ============================================================


@router.post(
    "",
    response_model=InvestigationEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation_evidence(
    payload: InvestigationEvidenceCreate,
    db: Session = Depends(get_db),
) -> InvestigationEvidence:
    """
    Link an evidence record to an investigation.
    """

    # --------------------------------------------------------
    # CHECK INVESTIGATION
    # --------------------------------------------------------

    investigation = (
        db.query(Investigation)
        .filter(
            Investigation.id == payload.investigation_id
        )
        .first()
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    # --------------------------------------------------------
    # CHECK EVIDENCE
    # --------------------------------------------------------

    evidence = (
        db.query(Evidence)
        .filter(
            Evidence.id == payload.evidence_id
        )
        .first()
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE LINK
    # --------------------------------------------------------

    existing = (
        db.query(InvestigationEvidence)
        .filter(
            InvestigationEvidence.investigation_id
            == payload.investigation_id,
            InvestigationEvidence.evidence_id
            == payload.evidence_id,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This evidence is already linked to the investigation.",
        )

    # --------------------------------------------------------
    # CREATE LINK
    # --------------------------------------------------------

    link = InvestigationEvidence(
        investigation_id=payload.investigation_id,
        evidence_id=payload.evidence_id,
        relation=payload.relation,
        notes=payload.notes,
    )

    try:
        db.add(link)
        db.commit()
        db.refresh(link)

        return link

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create investigation-evidence link.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create investigation-evidence link.",
        ) from exc


# ============================================================
# LIST LINKS
# ============================================================


@router.get(
    "",
    response_model=list[InvestigationEvidenceResponse],
)
def list_investigation_evidence(
    investigation_id: int | None = None,
    evidence_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[InvestigationEvidence]:
    """
    List investigation-evidence relationships.

    Optional filters:

        investigation_id
        evidence_id
    """

    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip cannot be negative.",
        )

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 500.",
        )

    query = db.query(InvestigationEvidence)

    if investigation_id is not None:

        if investigation_id < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="investigation_id must be greater than 0.",
            )

        query = query.filter(
            InvestigationEvidence.investigation_id
            == investigation_id
        )

    if evidence_id is not None:

        if evidence_id < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="evidence_id must be greater than 0.",
            )

        query = query.filter(
            InvestigationEvidence.evidence_id
            == evidence_id
        )

    return (
        query
        .order_by(
            InvestigationEvidence.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# GET SINGLE LINK
# ============================================================


@router.get(
    "/{link_id}",
    response_model=InvestigationEvidenceResponse,
)
def get_investigation_evidence(
    link_id: int,
    db: Session = Depends(get_db),
) -> InvestigationEvidence:
    """
    Retrieve one investigation-evidence relationship.
    """

    if link_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="link_id must be greater than 0.",
        )

    link = (
        db.query(InvestigationEvidence)
        .filter(
            InvestigationEvidence.id == link_id
        )
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation-evidence link not found.",
        )

    return link


# ============================================================
# UPDATE LINK
# ============================================================


@router.patch(
    "/{link_id}",
    response_model=InvestigationEvidenceResponse,
)
def update_investigation_evidence(
    link_id: int,
    payload: InvestigationEvidenceUpdate,
    db: Session = Depends(get_db),
) -> InvestigationEvidence:
    """
    Update the relationship between an investigation
    and evidence.

    Only supplied fields are changed.
    """

    if link_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="link_id must be greater than 0.",
        )

    link = (
        db.query(InvestigationEvidence)
        .filter(
            InvestigationEvidence.id == link_id
        )
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation-evidence link not found.",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    try:

        for field_name, value in updates.items():

            setattr(
                link,
                field_name,
                value,
            )

        db.commit()
        db.refresh(link)

        return link

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update investigation-evidence link.",
        ) from exc


# ============================================================
# DELETE LINK
# ============================================================


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_investigation_evidence(
    link_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Remove the relationship between an investigation
    and evidence.

    This does NOT delete the investigation or evidence itself.
    """

    if link_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="link_id must be greater than 0.",
        )

    link = (
        db.query(InvestigationEvidence)
        .filter(
            InvestigationEvidence.id == link_id
        )
        .first()
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation-evidence link not found.",
        )

    try:

        db.delete(link)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete investigation-evidence link.",
        ) from exc

    return None
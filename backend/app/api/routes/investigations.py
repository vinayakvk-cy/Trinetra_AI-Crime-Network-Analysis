from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.investigation import Investigation, InvestigationStatus
from app.models.investigation_evidence import InvestigationEvidence, InvestigationEvidenceRelation
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationUpdate,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


# ============================================================
# CREATE INVESTIGATION
# ============================================================

@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
) -> Investigation:
    """
    Create a new investigation.
    """

    data = payload.model_dump(
        exclude_unset=True
    )

    try:
        investigation = Investigation(
            **data
        )

        db.add(investigation)
        db.flush()

        # An investigation is scoped to a case. Newly created
        # investigations therefore inherit the case's existing
        # evidence as relevant investigation evidence so all
        # investigation-scoped consumers (analytics, assistant,
        # workspace and reports) immediately have real source data.
        case_evidence = (
            db.query(Evidence)
            .filter(
                Evidence.case_id == investigation.case_id,
                Evidence.deleted_at.is_(None),
            )
            .order_by(Evidence.id.asc())
            .all()
        )

        for evidence in case_evidence:
            db.add(
                InvestigationEvidence(
                    investigation_id=investigation.id,
                    evidence_id=evidence.id,
                    relation=InvestigationEvidenceRelation.RELEVANT,
                    notes="Automatically linked from the investigation's case evidence.",
                )
            )

        if investigation.status == InvestigationStatus.IN_PROGRESS:
            if investigation.started_at is None:
                investigation.started_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(investigation)

        return investigation

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create investigation: {str(exc)}",
        ) from exc


# ============================================================
# LIST INVESTIGATIONS
# ============================================================

@router.get(
    "",
    response_model=list[InvestigationResponse],
)
def list_investigations(
    case_id: int | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Investigation]:
    """
    Return a paginated list of investigations.

    Optional filters:

        case_id
        status_filter
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

    if case_id is not None and case_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_id must be greater than 0.",
        )

    query = db.query(Investigation)

    # --------------------------------------------------------
    # CASE FILTER
    # --------------------------------------------------------

    if case_id is not None:
        query = query.filter(
            Investigation.case_id == case_id
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    if status_filter:
        query = query.filter(
            Investigation.status
            == status_filter.strip().lower()
        )

    investigations = (
        query
        .order_by(
            Investigation.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []

    for investigation in investigations:
        case = (
            db.query(Case)
            .filter(Case.id == investigation.case_id)
            .first()
        )

        response = InvestigationResponse.model_validate(
            investigation
        )

        response.case_number = (
            case.case_number if case else None
        )
        response.case_title = (
            case.title if case else None
        )

        results.append(response)

    return results


# ============================================================
# GET INVESTIGATION
# ============================================================

@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
)
def get_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
) -> Investigation:
    """
    Retrieve a single investigation by ID.
    """

    if investigation_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="investigation_id must be greater than 0.",
        )

    investigation = (
        db.query(Investigation)
        .filter(
            Investigation.id == investigation_id
        )
        .first()
    )

    if investigation is None:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Investigation not found.",
    )

    case = (
        db.query(Case)
        .filter(Case.id == investigation.case_id)
        .first()
    )

    response = InvestigationResponse.model_validate(
        investigation
    )

    response.case_number = (
        case.case_number if case else None
    )

    response.case_title = (
        case.title if case else None
    )

    return response


# ============================================================
# UPDATE INVESTIGATION
# ============================================================

@router.patch(
    "/{investigation_id}",
    response_model=InvestigationResponse,
)
def update_investigation(
    investigation_id: int,
    payload: InvestigationUpdate,
    db: Session = Depends(get_db),
) -> Investigation:
    """
    Partially update an investigation.

    Only fields supplied in the PATCH request
    are changed.
    """

    if investigation_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="investigation_id must be greater than 0.",
        )

    investigation = (
        db.query(Investigation)
        .filter(
            Investigation.id == investigation_id
        )
        .first()
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    # --------------------------------------------------------
    # VERIFY DATABASE FIELDS
    # --------------------------------------------------------

    investigation_columns = {
        column.name
        for column in Investigation.__table__.columns
    }

    invalid_fields = [
        field
        for field in updates
        if field not in investigation_columns
    ]

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid investigation field(s).",
                "fields": invalid_fields,
            },
        )

    try:

        for field_name, value in updates.items():
            setattr(
                investigation,
                field_name,
                value,
            )

        db.commit()
        db.refresh(investigation)

        return investigation

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update investigation: {str(exc)}",
        ) from exc


# ============================================================
# DELETE INVESTIGATION
# ============================================================

@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an investigation.
    """

    if investigation_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="investigation_id must be greater than 0.",
        )

    investigation = (
        db.query(Investigation)
        .filter(
            Investigation.id == investigation_id
        )
        .first()
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    try:

        db.delete(investigation)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete investigation: {str(exc)}",
        ) from exc

    return None
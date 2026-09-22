from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.case import Case
from app.schemas.case import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/cases",
    tags=["Cases"],
)


# ============================================================
# CREATE CASE
# ============================================================

@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
) -> Case:
    """
    Create a new investigation case.
    """

    data = payload.model_dump(
        exclude_unset=True
    )

    try:
        case = Case(**data)

        db.add(case)
        db.commit()
        db.refresh(case)

        return case

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case: {str(exc)}",
        ) from exc


# ============================================================
# LIST CASES
# ============================================================

@router.get(
    "",
    response_model=list[CaseResponse],
)
def list_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Case]:

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

    return (
        db.query(Case)
        .order_by(Case.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# GET CASE
# ============================================================

@router.get(
    "/{case_id}",
    response_model=CaseResponse,
)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
) -> Case:

    if case_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_id must be greater than 0.",
        )

    case = (
        db.query(Case)
        .filter(Case.id == case_id)
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    return case


# ============================================================
# UPDATE CASE
# ============================================================

@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
)
def update_case(
    case_id: int,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
) -> Case:

    if case_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_id must be greater than 0.",
        )

    case = (
        db.query(Case)
        .filter(Case.id == case_id)
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    # Only allow fields that actually exist
    # in the Case SQLAlchemy model.
    case_columns = {
        column.name
        for column in Case.__table__.columns
    }

    invalid_fields = [
        field
        for field in updates
        if field not in case_columns
    ]

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid case field(s).",
                "fields": invalid_fields,
            },
        )

    try:

        for field_name, value in updates.items():
            setattr(
                case,
                field_name,
                value,
            )

        db.commit()
        db.refresh(case)

        return case

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case: {str(exc)}",
        ) from exc


# ============================================================
# DELETE CASE
# ============================================================

@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
) -> None:

    if case_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_id must be greater than 0.",
        )

    case = (
        db.query(Case)
        .filter(Case.id == case_id)
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    try:

        db.delete(case)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(exc)}",
        ) from exc

    return None
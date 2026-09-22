from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.case_entity import CaseEntity
from app.schemas.case_entity import (
    CaseEntityCreate,
    CaseEntityResponse,
    CaseEntityUpdate,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/case-entities",
    tags=["Case Entities"],
)


# ============================================================
# CREATE CASE ENTITY RELATIONSHIP
# ============================================================


@router.post(
    "",
    response_model=CaseEntityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case_entity(
    payload: CaseEntityCreate,
    db: Session = Depends(get_db),
) -> CaseEntity:
    """
    Connect an entity to a case.
    """

    # Check whether the relationship already exists.
    existing = (
        db.query(CaseEntity)
        .filter(
            CaseEntity.case_id == payload.case_id,
            CaseEntity.entity_id == payload.entity_id,
            CaseEntity.relation == payload.relation,
            CaseEntity.deleted_at.is_(None),
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This case-entity relationship already exists.",
        )

    try:
        case_entity = CaseEntity(
            **payload.model_dump(
                exclude_unset=True
            )
        )

        db.add(case_entity)
        db.commit()
        db.refresh(case_entity)

        return case_entity

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case-entity relationship: {str(exc)}",
        ) from exc


# ============================================================
# LIST CASE ENTITY RELATIONSHIPS
# ============================================================


@router.get(
    "",
    response_model=list[CaseEntityResponse],
)
def list_case_entities(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[CaseEntity]:

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
        db.query(CaseEntity)
        .filter(
            CaseEntity.deleted_at.is_(None)
        )
        .order_by(
            CaseEntity.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# GET CASE ENTITY RELATIONSHIP
# ============================================================


@router.get(
    "/{case_entity_id}",
    response_model=CaseEntityResponse,
)
def get_case_entity(
    case_entity_id: int,
    db: Session = Depends(get_db),
) -> CaseEntity:

    if case_entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_entity_id must be greater than 0.",
        )

    case_entity = (
        db.query(CaseEntity)
        .filter(
            CaseEntity.id == case_entity_id,
            CaseEntity.deleted_at.is_(None),
        )
        .first()
    )

    if case_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case-entity relationship not found.",
        )

    return case_entity


# ============================================================
# UPDATE CASE ENTITY RELATIONSHIP
# ============================================================


@router.patch(
    "/{case_entity_id}",
    response_model=CaseEntityResponse,
)
def update_case_entity(
    case_entity_id: int,
    payload: CaseEntityUpdate,
    db: Session = Depends(get_db),
) -> CaseEntity:

    if case_entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_entity_id must be greater than 0.",
        )

    case_entity = (
        db.query(CaseEntity)
        .filter(
            CaseEntity.id == case_entity_id,
            CaseEntity.deleted_at.is_(None),
        )
        .first()
    )

    if case_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case-entity relationship not found.",
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
                case_entity,
                field_name,
                value,
            )

        db.commit()
        db.refresh(case_entity)

        return case_entity

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case-entity relationship: {str(exc)}",
        ) from exc


# ============================================================
# DELETE CASE ENTITY RELATIONSHIP
# ============================================================


@router.delete(
    "/{case_entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_case_entity(
    case_entity_id: int,
    db: Session = Depends(get_db),
) -> None:

    if case_entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_entity_id must be greater than 0.",
        )

    case_entity = (
        db.query(CaseEntity)
        .filter(
            CaseEntity.id == case_entity_id,
            CaseEntity.deleted_at.is_(None),
        )
        .first()
    )

    if case_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case-entity relationship not found.",
        )

    try:
        # Soft delete instead of physically deleting.
        case_entity.mark_deleted()

        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case-entity relationship: {str(exc)}",
        ) from exc

    return None
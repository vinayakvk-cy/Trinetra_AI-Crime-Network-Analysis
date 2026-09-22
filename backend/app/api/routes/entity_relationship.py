from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from app.schemas.entity_relationship import (
    EntityRelationshipCreate,
    EntityRelationshipResponse,
    EntityRelationshipUpdate,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/entity-relationships",
    tags=["Entity Relationships"],
)


# ============================================================
# CREATE RELATIONSHIP
# ============================================================

@router.post(
    "",
    response_model=EntityRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity_relationship(
    payload: EntityRelationshipCreate,
    db: Session = Depends(get_db),
) -> EntityRelationship:
    """
    Create a relationship between two entities.
    """

    # --------------------------------------------------------
    # Prevent self relationship
    # --------------------------------------------------------

    if payload.source_entity_id == payload.target_entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target entities cannot be the same.",
        )

    # --------------------------------------------------------
    # Verify source entity
    # --------------------------------------------------------

    source_entity = (
        db.query(Entity)
        .filter(
            Entity.id == payload.source_entity_id,
            Entity.deleted_at.is_(None),
        )
        .first()
    )

    if source_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source entity not found.",
        )

    # --------------------------------------------------------
    # Verify target entity
    # --------------------------------------------------------

    target_entity = (
        db.query(Entity)
        .filter(
            Entity.id == payload.target_entity_id,
            Entity.deleted_at.is_(None),
        )
        .first()
    )

    if target_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target entity not found.",
        )

    # --------------------------------------------------------
    # Prevent duplicate relationship
    # --------------------------------------------------------

    existing_relationship = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.source_entity_id
            == payload.source_entity_id,
            EntityRelationship.target_entity_id
            == payload.target_entity_id,
            EntityRelationship.relationship_type
            == payload.relationship_type,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )

    if existing_relationship is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This entity relationship already exists.",
        )

    # --------------------------------------------------------
    # Create relationship
    # --------------------------------------------------------

    relationship = EntityRelationship(
        **payload.model_dump(
            exclude_unset=True
        )
    )

    try:
        db.add(relationship)
        db.commit()
        db.refresh(relationship)

        return relationship

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entity relationship.",
        ) from exc


# ============================================================
# LIST RELATIONSHIPS
# ============================================================

@router.get(
    "",
    response_model=list[EntityRelationshipResponse],
)
def list_entity_relationships(
    source_entity_id: int | None = None,
    target_entity_id: int | None = None,
    relationship_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[EntityRelationship]:
    """
    List entity relationships with optional filters.
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

    query = db.query(EntityRelationship).filter(
        EntityRelationship.deleted_at.is_(None)
    )

    if source_entity_id is not None:

        if source_entity_id < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_entity_id must be greater than 0.",
            )

        query = query.filter(
            EntityRelationship.source_entity_id
            == source_entity_id
        )

    if target_entity_id is not None:

        if target_entity_id < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_entity_id must be greater than 0.",
            )

        query = query.filter(
            EntityRelationship.target_entity_id
            == target_entity_id
        )

    if relationship_type:

        query = query.filter(
            EntityRelationship.relationship_type
            == relationship_type.strip().lower()
        )

    return (
        query
        .order_by(
            EntityRelationship.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# GET RELATIONSHIP
# ============================================================

@router.get(
    "/{relationship_id}",
    response_model=EntityRelationshipResponse,
)
def get_entity_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
) -> EntityRelationship:
    """
    Retrieve a single entity relationship.
    """

    if relationship_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relationship_id must be greater than 0.",
        )

    relationship = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.id == relationship_id,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity relationship not found.",
        )

    return relationship


# ============================================================
# UPDATE RELATIONSHIP
# ============================================================

@router.patch(
    "/{relationship_id}",
    response_model=EntityRelationshipResponse,
)
def update_entity_relationship(
    relationship_id: int,
    payload: EntityRelationshipUpdate,
    db: Session = Depends(get_db),
) -> EntityRelationship:
    """
    Partially update an entity relationship.
    """

    if relationship_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relationship_id must be greater than 0.",
        )

    relationship = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.id == relationship_id,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity relationship not found.",
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
    # Check duplicate if relationship type changes
    # --------------------------------------------------------

    new_relationship_type = updates.get(
        "relationship_type",
        relationship.relationship_type,
    )

    duplicate = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.id != relationship.id,
            EntityRelationship.source_entity_id
            == relationship.source_entity_id,
            EntityRelationship.target_entity_id
            == relationship.target_entity_id,
            EntityRelationship.relationship_type
            == new_relationship_type,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another relationship with the same type already exists.",
        )

    try:
        for field_name, value in updates.items():
            setattr(
                relationship,
                field_name,
                value,
            )

        db.commit()
        db.refresh(relationship)

        return relationship

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entity relationship.",
        ) from exc


# ============================================================
# DELETE RELATIONSHIP
# ============================================================

@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entity_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft-delete an entity relationship.
    """

    if relationship_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relationship_id must be greater than 0.",
        )

    relationship = (
        db.query(EntityRelationship)
        .filter(
            EntityRelationship.id == relationship_id,
            EntityRelationship.deleted_at.is_(None),
        )
        .first()
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity relationship not found.",
        )

    try:
        relationship.mark_deleted()

        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entity relationship.",
        ) from exc

    return None
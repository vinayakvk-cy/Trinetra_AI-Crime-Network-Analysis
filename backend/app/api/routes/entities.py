from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.entity import (
    Entity,
    EntityType,
    EntitySource,
)
from app.schemas.entity import (
    EntityCreate,
    EntityResponse,
    EntityUpdate,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/entities",
    tags=["Entities"],
)


# ============================================================
# CREATE ENTITY
# ============================================================

@router.post(
    "",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity(
    payload: EntityCreate,
    db: Session = Depends(get_db),
) -> Entity:
    """
    Create a new investigation entity.
    """

    data = payload.model_dump(
        exclude_unset=True
    )

    # --------------------------------------------------------
    # metadata is currently not a database column in Entity.
    # Remove it before creating the SQLAlchemy object.
    # --------------------------------------------------------

    data.pop("metadata", None)

    try:
        entity = Entity(**data)

        db.add(entity)
        db.commit()
        db.refresh(entity)

        return entity

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity: {str(exc)}",
        ) from exc


# ============================================================
# LIST ENTITIES
# ============================================================

@router.get(
    "",
    response_model=list[EntityResponse],
)
def list_entities(
    entity_type: EntityType | None = None,
    source: EntitySource | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Entity]:

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

    query = db.query(Entity)

    if entity_type is not None:
        query = query.filter(
            Entity.entity_type == entity_type
        )

    if source is not None:
        query = query.filter(
            Entity.source == source
        )

    return (
        query
        .order_by(Entity.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================
# SEARCH ENTITIES
# ============================================================

@router.get(
    "/search/",
    response_model=list[EntityResponse],
)
def search_entities(
    q: str,
    entity_type: EntityType | None = None,
    source: EntitySource | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[Entity]:

    q = q.strip()

    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    if len(q) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query is too long.",
        )

    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 200.",
        )

    search_term = f"%{q}%"

    query = db.query(Entity).filter(
        or_(
            Entity.name.ilike(search_term),
            Entity.normalized_name.ilike(search_term),
            Entity.external_id.ilike(search_term),
            Entity.source_reference.ilike(search_term),
            Entity.description.ilike(search_term),
        )
    )

    if entity_type is not None:
        query = query.filter(
            Entity.entity_type == entity_type
        )

    if source is not None:
        query = query.filter(
            Entity.source == source
        )

    return (
        query
        .order_by(Entity.id.desc())
        .limit(limit)
        .all()
    )


# ============================================================
# GET ENTITY
# ============================================================

@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
)
def get_entity(
    entity_id: int,
    db: Session = Depends(get_db),
) -> Entity:

    if entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_id must be greater than 0.",
        )

    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id)
        .first()
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
        )

    return entity


# ============================================================
# UPDATE ENTITY
# ============================================================

@router.patch(
    "/{entity_id}",
    response_model=EntityResponse,
)
def update_entity(
    entity_id: int,
    payload: EntityUpdate,
    db: Session = Depends(get_db),
) -> Entity:

    if entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_id must be greater than 0.",
        )

    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id)
        .first()
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
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
    # metadata is currently not a database column.
    # --------------------------------------------------------

    updates.pop("metadata", None)

    # --------------------------------------------------------
    # Only update actual Entity model columns.
    # --------------------------------------------------------

    entity_columns = {
        column.name
        for column in Entity.__table__.columns
    }

    invalid_fields = [
        field
        for field in updates
        if field not in entity_columns
    ]

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid entity field(s).",
                "fields": invalid_fields,
            },
        )

    try:
        for field_name, value in updates.items():
            setattr(
                entity,
                field_name,
                value,
            )

        db.commit()
        db.refresh(entity)

        return entity

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity: {str(exc)}",
        ) from exc


# ============================================================
# DELETE ENTITY
# ============================================================

@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
) -> None:

    if entity_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_id must be greater than 0.",
        )

    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id)
        .first()
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
        )

    try:
        db.delete(entity)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity: {str(exc)}",
        ) from exc

    return None
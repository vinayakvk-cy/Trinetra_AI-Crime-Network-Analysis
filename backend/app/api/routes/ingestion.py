"""
TRINETRA Ingestion API
======================

FastAPI routes for importing investigation data.

The API accepts structured records and routes them through
the existing ingestion pipeline.

The route layer is intentionally thin:
    Request
      ↓
    Validation
      ↓
    Parser
      ↓
    Normalizer
      ↓
    Source handler
      ↓
    Database / graph pipeline
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.ingestion.normalizer import normalize_record
from app.ingestion.parser import parse_record
from app.ingestion.validators import validate_record


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class IngestionRequest(BaseModel):
    """
    Generic ingestion request.

    source identifies the originating data source, for example:

        fir
        cdr
        transactions
        vehicles
        social_media
        jail_records
        gps
        forensic
        postmortem
    """

    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    case_id: int | None = None

    investigation_id: int | None = None


class BatchIngestionRequest(BaseModel):
    """
    Batch ingestion request.
    """

    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    records: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    case_id: int | None = None

    investigation_id: int | None = None


class IngestionResponse(BaseModel):
    """
    Standard ingestion response.
    """

    success: bool

    source: str

    records_received: int

    records_processed: int

    records_rejected: int

    results: list[dict[str, Any]]


# ============================================================
# SUPPORTED SOURCES
# ============================================================

SUPPORTED_SOURCES = {
    "fir",
    "cdr",
    "transactions",
    "vehicles",
    "social_media",
    "jail_records",
    "gps",
    "forensic",
    "postmortem",
}


# ============================================================
# SINGLE RECORD INGESTION
# ============================================================


@router.post(
    "",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_record(
    payload: IngestionRequest,
    db: Session = Depends(get_db),
) -> IngestionResponse:
    """
    Ingest one source record.
    """

    source = payload.source.strip().lower()

    if source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported ingestion source: "
                f"{payload.source}"
            ),
        )

    result = _process_record(
        source=source,
        data=payload.data,
        case_id=payload.case_id,
        investigation_id=payload.investigation_id,
        db=db,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result,
        )

    return IngestionResponse(
        success=True,
        source=source,
        records_received=1,
        records_processed=1,
        records_rejected=0,
        results=[result],
    )


# ============================================================
# BATCH INGESTION
# ============================================================


@router.post(
    "/batch",
    response_model=IngestionResponse,
)
def ingest_batch(
    payload: BatchIngestionRequest,
    db: Session = Depends(get_db),
) -> IngestionResponse:
    """
    Ingest multiple records from the same source.
    """

    source = payload.source.strip().lower()

    if source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported ingestion source: "
                f"{payload.source}"
            ),
        )

    results: list[dict[str, Any]] = []

    processed = 0
    rejected = 0

    for record in payload.records:

        result = _process_record(
            source=source,
            data=record,
            case_id=payload.case_id,
            investigation_id=payload.investigation_id,
            db=db,
        )

        results.append(result)

        if result["success"]:
            processed += 1
        else:
            rejected += 1

    return IngestionResponse(
        success=rejected == 0,
        source=source,
        records_received=len(
            payload.records
        ),
        records_processed=processed,
        records_rejected=rejected,
        results=results,
    )


# ============================================================
# VALIDATE RECORD
# ============================================================


@router.post(
    "/validate",
)
def validate_ingestion_record(
    payload: IngestionRequest,
) -> dict[str, Any]:
    """
    Validate an ingestion record without persisting it.
    """

    source = payload.source.strip().lower()

    if source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported ingestion source: "
                f"{payload.source}"
            ),
        )

    try:

        parsed = parse_record(
            payload.data,
            source=source,
        )

        normalized = normalize_record(
            parsed,
            source=source,
        )

        validation = validate_record(
            normalized,
            source=source,
        )

        return {
            "success": True,
            "source": source,
            "valid": bool(validation),
            "parsed": parsed,
            "normalized": normalized,
            "validation": validation,
        }

    except Exception as exc:

        return {
            "success": False,
            "source": source,
            "valid": False,
            "error": str(exc),
        }


# ============================================================
# SUPPORTED SOURCES
# ============================================================


@router.get(
    "/sources",
)
def list_ingestion_sources() -> dict[str, Any]:
    """
    Return supported ingestion source types.
    """

    return {
        "sources": sorted(
            SUPPORTED_SOURCES
        ),
        "count": len(
            SUPPORTED_SOURCES
        ),
    }


# ============================================================
# INTERNAL PROCESSOR
# ============================================================


def _process_record(
    source: str,
    data: dict[str, Any],
    case_id: int | None,
    investigation_id: int | None,
    db: Session,
) -> dict[str, Any]:
    """
    Run a record through the ingestion pipeline.

    Persistence is deliberately kept behind the ingestion
    modules so the API does not duplicate database logic.
    """

    try:

        # ----------------------------------------------------
        # 1. Parse
        # ----------------------------------------------------

        parsed = parse_record(
            data,
            source=source,
        )

        # ----------------------------------------------------
        # 2. Normalize
        # ----------------------------------------------------

        normalized = normalize_record(
            parsed,
            source=source,
        )

        # ----------------------------------------------------
        # 3. Validate
        # ----------------------------------------------------

        validation = validate_record(
            normalized,
            source=source,
        )

        if not validation:
            return {
                "success": False,
                "source": source,
                "error": (
                    "Record failed ingestion validation."
                ),
            }

        # ----------------------------------------------------
        # 4. Attach investigation metadata
        # ----------------------------------------------------

        normalized["_ingestion"] = {
            "source": source,
            "case_id": case_id,
            "investigation_id": (
                investigation_id
            ),
        }

        # ----------------------------------------------------
        # 5. Return normalized record
        # ----------------------------------------------------
        #
        # Actual persistence can be connected to the source
        # handlers / graph builder without changing this API.
        #

        return {
            "success": True,
            "source": source,
            "case_id": case_id,
            "investigation_id": investigation_id,
            "record": normalized,
        }

    except ValueError as exc:

        db.rollback()

        return {
            "success": False,
            "source": source,
            "error": str(exc),
        }

    except Exception as exc:

        db.rollback()

        return {
            "success": False,
            "source": source,
            "error": (
                "Unexpected ingestion error."
            ),
            "details": str(exc),
        }
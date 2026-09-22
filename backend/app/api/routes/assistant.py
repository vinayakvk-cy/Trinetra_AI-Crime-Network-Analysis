"""
TRINETRA Assistant API
======================

FastAPI routes for the investigation assistant.

Responsibilities
----------------
- Retrieve investigation context
- Ask the local assistant questions
- Provide investigation-aware answers
- Return supporting context used by the assistant

The route layer does not implement assistant reasoning.
It delegates that work to:
    app.assistant.context_retriever
    app.assistant.local_assistant
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.assistant.context_retriever import (
    ContextRetriever,
)
from app.assistant.local_assistant import (
    LocalAssistant,
)
from app.db.database import get_db
from sqlalchemy.orm import Session

from app.core.config import settings
from app.graph.neo4j_client import Neo4jClient


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)

def get_neo4j_client() -> Neo4jClient:
    return Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class AssistantRequest(BaseModel):
    """
    Request sent to the investigation assistant.
    """

    investigation_id: int | None = None

    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    context_limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class ContextRequest(BaseModel):
    """
    Request for investigation context.
    """

    investigation_id: int

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class AssistantResponse(BaseModel):
    """
    Standard assistant response.
    """

    success: bool

    answer: str

    investigation_id: int | None = None

    context: Any = None


# ============================================================
# HEALTH
# ============================================================


@router.get(
    "/health",
)
def assistant_health() -> dict[str, Any]:
    """
    Check whether the assistant API is available.
    """

    return {
        "success": True,
        "assistant": "available",
    }


# ============================================================
# CONTEXT RETRIEVAL
# ============================================================


@router.post(
    "/context",
)
def retrieve_context(
    payload: ContextRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve relevant investigation context without
    generating an assistant response.
    """

    try:

        neo4j_client = get_neo4j_client()

        retriever = ContextRetriever(
            session=db,
            neo4j_client=neo4j_client,
        )

        context = retriever.retrieve(
            investigation_id=(
                payload.investigation_id
            ),
            memory_limit=payload.limit,
        )

        return {
            "success": True,
            "investigation_id": (
                payload.investigation_id
            ),
            "context": _serialize(
                context
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except AttributeError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "ContextRetriever does not expose "
                f"the expected method: {exc}"
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Context retrieval failed: {exc}"
            ),
        )


# ============================================================
# ASK ASSISTANT
# ============================================================


@router.post(
    "/ask",
    response_model=AssistantResponse,
)
def ask_assistant(
    payload: AssistantRequest,
    db: Session = Depends(get_db),
) -> AssistantResponse:
    """
    Ask the local investigation assistant a question.

    If an investigation_id is supplied, the assistant retrieves
    investigation-specific context automatically.
    """

    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    try:

        neo4j_client = get_neo4j_client()

        assistant = LocalAssistant(
            db,
            neo4j_client=neo4j_client,
        )

        answer = assistant.ask(
            question=question,
            investigation_id=(
                payload.investigation_id
            ),
        )

        context = None

        if payload.investigation_id is not None:

            retriever = ContextRetriever(
                db,
                neo4j_client=neo4j_client,
            )

            context = retriever.retrieve_query_context(
                investigation_id=(
                    payload.investigation_id
                ),
                query=question,
                memory_limit=payload.context_limit,
            )

        return AssistantResponse(
            success=True,
            answer=_extract_answer(
                answer
            ),
            investigation_id=(
                payload.investigation_id
            ),
            context=_serialize(
                context
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except AttributeError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "LocalAssistant does not expose "
                f"the expected method: {exc}"
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Assistant request failed: {exc}"
            ),
        )


# ============================================================
# INVESTIGATION ASSISTANT
# ============================================================


@router.post(
    "/investigations/{investigation_id}/ask",
)
def ask_investigation_assistant(
    investigation_id: int,
    question: str,
    context_limit: int = 20,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Convenience endpoint for asking a question against a
    specific investigation.
    """

    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    if context_limit < 1 or context_limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "context_limit must be between "
                "1 and 100."
            ),
        )

    try:

        neo4j_client = get_neo4j_client()

        assistant = LocalAssistant(
            db,
            neo4j_client=neo4j_client,
)

        answer = assistant.ask(
            question=question,
            investigation_id=investigation_id,
        )

        retriever = ContextRetriever(
    session=db,
    neo4j_client=neo4j_client,
)

        context = retriever.retrieve_query_context(
            investigation_id=investigation_id,
            query=question,
            memory_limit=context_limit,
        )

        return {
            "success": True,
            "investigation_id": (
                investigation_id
            ),
            "question": question,
            "answer": _extract_answer(
                answer
            ),
            "context": _serialize(
                context
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Investigation assistant failed: "
                f"{exc}"
            ),
        )


# ============================================================
# SERIALIZATION
# ============================================================


def _serialize(
    value: Any,
) -> Any:
    """
    Convert internal objects into JSON-compatible values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _serialize(item)
            for item in value
        ]

    if hasattr(
        value,
        "model_dump",
    ):
        return _serialize(
            value.model_dump()
        )

    if hasattr(
        value,
        "__table__",
    ):
        return {
            column.name: _serialize(
                getattr(
                    value,
                    column.name,
                )
            )
            for column
            in value.__table__.columns
        }

    if hasattr(
        value,
        "__dict__",
    ):
        return {
            key: _serialize(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


# ============================================================
# ANSWER EXTRACTION
# ============================================================


def _extract_answer(
    value: Any,
) -> str:
    """
    Normalize different possible assistant return formats
    into a string suitable for the API response.
    """

    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        for key in (
            "answer",
            "response",
            "text",
            "content",
        ):
            if key in value:
                return str(
                    value[key]
                )

    if hasattr(
        value,
        "answer",
    ):
        return str(
            value.answer
        )

    return str(value)
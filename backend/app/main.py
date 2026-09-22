from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.assistant import router as assistant_router
from app.api.routes.reports import router as reports_router
from app.api.routes.graph import router as graph_router
from app.api.routes.analytics import router as analytics_router
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.cases import router as case_router
from app.api.routes.entities import router as entity_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.investigations import (
    router as investigation_router,
)
from app.api.routes.investigation_evidence import (
    router as investigation_evidence_router,
)

from app.db.database import (
    check_database_connection,
    close_database,
    init_db,
)
from app.api.routes.investigation_evidence import (
    router as investigation_evidence_router,
)
from app.db.database import (
    check_database_connection,
    close_database,
    init_db,
)

from app.api.routes.entity_relationship import (
    router as entity_relationship_router,
)

from app.api.routes.case_entity import router as case_entity_router


# ============================================================
# APPLICATION LIFESPAN
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """

    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------

    print("TRINETRA API starting...")

    try:
        init_db()
        print("Database initialized successfully.")

    except Exception as exc:
        print(
            f"Database initialization failed: {exc}"
        )
        raise

    # --------------------------------------------------------
    # DATABASE HEALTH CHECK
    # --------------------------------------------------------

    if check_database_connection():
        print("Database connection successful.")
    else:
        print("WARNING: Database connection failed.")

    yield

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    print("TRINETRA API shutting down...")

    close_database()

    print("Database connections closed.")


# ============================================================
# FASTAPI APPLICATION
# ============================================================


app = FastAPI(
    title="TRINETRA Investigation API",
    description=(
        "TRINETRA investigation and intelligence management API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================


app.include_router(case_router)

app.include_router(investigation_router)

app.include_router(evidence_router)

app.include_router(entity_router)

app.include_router(
    investigation_evidence_router
)

app.include_router(
    entity_relationship_router
)

app.include_router(case_entity_router)
app.include_router(assistant_router)
app.include_router(reports_router)
app.include_router(graph_router)
app.include_router(analytics_router)

# ============================================================
# ROOT ENDPOINT
# ============================================================


@app.get(
    "/",
    tags=["System"],
)
def root() -> dict[str, str]:
    """
    Basic API health/status endpoint.
    """

    return {
        "message": "TRINETRA API is running",
        "version": "1.0.0",
        "status": "active",
    }


# ============================================================
# HEALTH CHECK
# ============================================================


@app.get(
    "/health",
    tags=["System"],
)
def health_check() -> dict[str, object]:
    """
    Check API and database health.
    """

    database_status = check_database_connection()

    return {
        "status": "healthy" if database_status else "unhealthy",
        "database": (
            "connected"
            if database_status
            else "disconnected"
        ),
    }
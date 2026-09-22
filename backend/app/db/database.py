from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ============================================================
# DATABASE URL
# ============================================================

DATABASE_URL = settings.database_url


# ============================================================
# ENGINE
# ============================================================

connect_args: dict = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


# ============================================================
# BASE
# ============================================================

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    """

    pass


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session to FastAPI endpoints.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """
    Import all ORM models and create missing tables.

    IMPORTANT:
    All models must be imported before Base.metadata.create_all()
    so SQLAlchemy knows about every table.
    """

    # ========================================================
    # IMPORT ALL ORM MODELS
    # ========================================================

    from app.models.case import Case  # noqa: F401
    from app.models.entity import Entity  # noqa: F401
    from app.models.evidence import Evidence  # noqa: F401
    from app.models.investigation import Investigation  # noqa: F401
    from app.models.investigation_evidence import InvestigationEvidence  # noqa: F401

    # Investigation ↔ Evidence connection
    from app.models.investigation_evidence import (
        InvestigationEvidence,
    )  # noqa: F401

    from app.models.entity_relationship import (
    EntityRelationship,
    )  # noqa: F401

    from app.models.case_entity import CaseEntity  # noqa: F401

    # ========================================================
    # CREATE MISSING TABLES
    # ========================================================

    Base.metadata.create_all(
        bind=engine
    )


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

def check_database_connection() -> bool:
    """
    Check whether the database is reachable.
    """

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False


# ============================================================
# DATABASE SHUTDOWN
# ============================================================

def close_database() -> None:
    """
    Dispose SQLAlchemy connection pool.
    """

    engine.dispose()
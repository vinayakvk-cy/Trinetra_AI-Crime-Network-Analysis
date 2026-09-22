
from app.api.routes.cases import router as cases_router
from app.api.routes.entities import router as entities_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.investigations import router as investigations_router


__all__ = [
    "cases_router",
    "entities_router",
    "evidence_router",
    "investigations_router",
]
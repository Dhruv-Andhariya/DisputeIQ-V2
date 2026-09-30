from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.permissions import Permission
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.core.errors import error_responses
from app.document_intelligence import service
from app.document_intelligence.schemas import ProcessingResponse
from app.users.models import User

router = APIRouter(prefix="/domain", tags=["Document Intelligence"])
DB = Annotated[Session, Depends(get_db)]
Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_CASES))]
Investigator = Annotated[User, Depends(require_permission(Permission.INVESTIGATE))]


@router.post("/evidence/{evidence_id}/process", response_model=ProcessingResponse,
             responses=error_responses(401, 403, 404))
def process_evidence(evidence_id: str, db: DB, user: Investigator):
    return service.process(db, evidence_id, user.organization_id, user.id)


@router.get("/evidence/{evidence_id}/processing", response_model=ProcessingResponse,
            responses=error_responses(401, 403, 404))
def get_processing_result(evidence_id: str, db: DB, user: Viewer):
    return service.latest(db, evidence_id, user.organization_id)

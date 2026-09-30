from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.core.database import get_db
from app.core.errors import error_responses
from app.evidence import service
from app.evidence.schemas import EvidenceResponse, EvidenceUpdate
from app.users.models import User

router = APIRouter(prefix="/domain", tags=["Evidence"])
DB = Annotated[Session, Depends(get_db)]
Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_CASES))]
Investigator = Annotated[User, Depends(require_permission(Permission.INVESTIGATE))]
Admin = Annotated[User, Depends(require_permission(Permission.MANAGE_ORGANIZATION))]


@router.post("/disputes/{dispute_id}/evidence", response_model=EvidenceResponse, status_code=201,
             responses=error_responses(400, 401, 403, 404, 409))
def upload_evidence(
    dispute_id: str,
    db: DB,
    user: Investigator,
    evidence_type: str = Form(...),
    source_type: str = Form("MERCHANT_UPLOAD"),
    file: UploadFile = File(...),
):
    return service.create_record(
        db, dispute_id=dispute_id, evidence_type=evidence_type, source_type=source_type,
        upload=file, organization_id=user.organization_id, actor_user_id=user.id,
    )


@router.get("/disputes/{dispute_id}/evidence", response_model=List[EvidenceResponse],
            responses=error_responses(401, 403, 404))
def list_evidence(dispute_id: str, db: DB, user: Viewer):
    return service.list_for_dispute(db, dispute_id, user.organization_id)


@router.get("/evidence/{evidence_id}/download", responses=error_responses(401, 403, 404))
def download_evidence(evidence_id: str, db: DB, user: Viewer):
    record, content = service.download_record(db, evidence_id, user.organization_id)
    return Response(
        content=content,
        media_type=record.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{record.original_filename}"'},
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse, responses=error_responses(401, 403, 404))
def get_evidence(evidence_id: str, db: DB, user: Viewer):
    return service.to_response_data(service.get_record(db, evidence_id, user.organization_id))


@router.patch("/evidence/{evidence_id}", response_model=EvidenceResponse, responses=error_responses(401, 403, 404))
def update_evidence(evidence_id: str, data: EvidenceUpdate, db: DB, user: Investigator):
    return service.update_record(db, evidence_id, data, user.organization_id, user.id)


@router.delete("/evidence/{evidence_id}", status_code=204, responses=error_responses(401, 403, 404))
def delete_evidence(evidence_id: str, db: DB, user: Admin):
    service.delete_record(db, evidence_id, user.organization_id, user.id)
    return Response(status_code=204)

"""
Dispute investigation API.

Every route requires authentication, and every data access is scoped to
`user.organization_id`. A dispute owned by another organization is indistinguishable
from one that doesn't exist (404).
"""
import json
import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission, has_permission
from app.core.config import BASE_DIR
from app.core.errors import error_responses
from app.models.domain import Dispute, Investigation, Evidence, TimelineEvent, AuditEvent
from app.database.db import get_all_disputes, get_dispute_by_id, get_investigation_by_dispute_id
from app.services.dispute_service import DisputeService
from app.services.evidence_retrieval import EvidenceRetrievalService
from app.services.audit_service import AuditService
from app.users.models import User

logger = logging.getLogger("disputeiq.api")

router = APIRouter(tags=["Disputes"])

Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_CASES))]
Investigator = Annotated[User, Depends(require_permission(Permission.INVESTIGATE))]
Reviewer = Annotated[User, Depends(require_permission(Permission.REVIEW_CASES))]

READ_ERRORS = error_responses(401, 403, 404)

class HumanActionRequest(BaseModel):
    notes: Optional[str] = None

class DemoFailureRequest(BaseModel):
    dispute_id: str


def _dispute_or_404(dispute_id: str, user: User) -> Dispute:
    dispute = get_dispute_by_id(dispute_id, organization_id=user.organization_id)
    if not dispute:
        raise HTTPException(status_code=404, detail=f"Dispute {dispute_id} not found.")
    return dispute


@router.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": "DisputeIQ AI Risk Manager API", "version": "2.0.0"}

@router.get("/disputes", response_model=List[Dispute], responses=error_responses(401, 403))
def list_disputes(user: Viewer):
    return get_all_disputes(organization_id=user.organization_id)

@router.get("/disputes/{dispute_id}", response_model=Dispute, responses=READ_ERRORS)
def get_dispute(dispute_id: str, user: Viewer):
    return _dispute_or_404(dispute_id, user)

@router.get("/disputes/{dispute_id}/investigation", response_model=Investigation, responses=READ_ERRORS,
            summary="Latest investigation result (read-only)")
def get_latest_investigation(dispute_id: str, user: Viewer):
    _dispute_or_404(dispute_id, user)
    inv = get_investigation_by_dispute_id(dispute_id, organization_id=user.organization_id)
    if not inv:
        raise HTTPException(status_code=404, detail="No investigation has been run for this dispute yet.")
    return inv

@router.post("/disputes/{dispute_id}/investigate", response_model=Investigation, responses=READ_ERRORS)
def investigate_dispute(dispute_id: str, user: Investigator):
    try:
        return DisputeService.run_investigation(
            dispute_id, organization_id=user.organization_id, actor_user_id=user.id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception:
        logger.exception("Investigation pipeline failed for dispute_id=%s", dispute_id)
        raise HTTPException(status_code=500, detail="Investigation failed due to an internal error.")

@router.get("/disputes/{dispute_id}/evidence", response_model=List[Evidence], responses=READ_ERRORS)
def get_dispute_evidence(dispute_id: str, user: Viewer):
    _dispute_or_404(dispute_id, user)
    return EvidenceRetrievalService.retrieve_evidence(dispute_id, organization_id=user.organization_id)

@router.get("/disputes/{dispute_id}/timeline", response_model=List[TimelineEvent], responses=READ_ERRORS)
def get_dispute_timeline(dispute_id: str, user: Viewer):
    _dispute_or_404(dispute_id, user)
    inv = get_investigation_by_dispute_id(dispute_id, organization_id=user.organization_id)
    if not inv:
        # Building the timeline runs the pipeline, which is a write; read-only roles can't trigger it.
        if not has_permission(user.role, Permission.INVESTIGATE):
            raise HTTPException(status_code=404, detail="No investigation has been run for this dispute yet.")
        inv = DisputeService.run_investigation(
            dispute_id, organization_id=user.organization_id, actor_user_id=user.id
        )
    return inv.timeline

@router.get("/disputes/{dispute_id}/audit", response_model=List[AuditEvent], responses=READ_ERRORS)
def get_dispute_audit(dispute_id: str, user: Viewer):
    _dispute_or_404(dispute_id, user)
    return AuditService.get_audit_trail(dispute_id, organization_id=user.organization_id)

@router.post("/disputes/{dispute_id}/approve", responses=READ_ERRORS)
def approve_dispute(dispute_id: str, user: Reviewer, req: HumanActionRequest = HumanActionRequest()):
    try:
        updated_dispute = DisputeService.approve_investigation(
            dispute_id, req.notes, organization_id=user.organization_id, actor_user_id=user.id
        )
        return {"status": "SUCCESS", "message": "Dispute approved and contest submitted.", "dispute": updated_dispute}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/disputes/{dispute_id}/reject", responses=READ_ERRORS)
def reject_dispute(dispute_id: str, user: Reviewer, req: HumanActionRequest = HumanActionRequest()):
    try:
        updated_dispute = DisputeService.reject_investigation(
            dispute_id, req.notes, organization_id=user.organization_id, actor_user_id=user.id
        )
        return {"status": "SUCCESS", "message": "Dispute rejected. Marked as accepted/closed.", "dispute": updated_dispute}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/demo/failure", response_model=Investigation, tags=["Demo"], responses=READ_ERRORS)
def trigger_demo_failure(req: DemoFailureRequest, user: Investigator):
    """
    Demonstrates SCENARIO 3: External API failure with bounded retries and safe degradation to HUMAN_REVIEW.
    """
    try:
        return DisputeService.simulate_system_failure(
            req.dispute_id, organization_id=user.organization_id, actor_user_id=user.id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.get("/evaluation/summary", tags=["System"], responses=error_responses(401, 403))
def get_evaluation_summary(user: Viewer):
    # The benchmark is global, so do not present it as an organization metric
    # when the current tenant has no dispute records to investigate.
    if not get_all_disputes(organization_id=user.organization_id):
        return {
            "status": "NOT_AVAILABLE",
            "message": "Benchmark evaluation is unavailable until this organization has disputes.",
        }

    eval_path = BASE_DIR / "evaluation" / "results" / "summary.json"
    if not eval_path.exists():
        return {
            "status": "NOT_RUN",
            "message": "Evaluation pipeline has not been executed yet. Run evaluation/evaluate.py to produce metrics."
        }
    with open(eval_path, "r") as f:
        return json.load(f)

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.permissions import Permission
from app.core.database import get_db
from app.core.errors import error_responses
from app.models.domain import AuditEvent
from app.organizations import service
from app.organizations.schemas import OrganizationResponse, OrganizationUpdateRequest
from app.services.audit_service import AuditService
from app.users.models import User

# "/me" makes it explicit that the organization is always the caller's own,
# resolved from the token, never an id supplied by the client.
router = APIRouter(prefix="/organizations/me", tags=["Organization"])

DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=OrganizationResponse, summary="The caller's organization",
            responses=error_responses(401))
def get_my_organization(user: CurrentUser):
    return user.organization


@router.patch("", response_model=OrganizationResponse, summary="Update organization details (ADMIN)",
              responses=error_responses(401, 403, 409))
def update_my_organization(
    data: OrganizationUpdateRequest,
    db: DB,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_ORGANIZATION))],
):
    org = user.organization
    changes = service.update_organization(db, org, data)
    if changes:
        AuditService.log_event(
            "ORGANIZATION_UPDATED", f"Organization details updated by {user.email}.", {"changes": changes},
            organization_id=org.id, actor_user_id=user.id, resource_type="ORGANIZATION", resource_id=org.id,
        )
    return org


@router.get("/audit-events", response_model=List[AuditEvent],
            summary="Recent organization-wide activity (ADMIN)", responses=error_responses(401, 403))
def get_organization_activity(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_ORGANIZATION_AUDIT))],
    limit: int = Query(50, ge=1, le=200),
):
    return AuditService.get_organization_activity(organization_id=user.organization_id, limit=limit)

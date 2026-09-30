from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.core.database import get_db
from app.core.errors import error_responses
from app.services.audit_service import AuditService
from app.users import service
from app.users.models import Role, User
from app.users.schemas import UserCreateRequest, UserSummary, UserUpdateRequest

# Membership management for the caller's own organization. There is no invitation email
# flow yet: an admin creates the account and shares the initial password out of band.
router = APIRouter(prefix="/organizations/me/users", tags=["Organization members"])

DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_permission(Permission.MANAGE_USERS))]


@router.get("", response_model=List[UserSummary], summary="List organization members (ADMIN)",
            responses=error_responses(401, 403))
def list_members(db: DB, admin: Admin):
    return service.list_users(db, organization_id=admin.organization_id)


@router.post("", response_model=UserSummary, status_code=status.HTTP_201_CREATED,
             summary="Create a user in the organization (ADMIN)", responses=error_responses(401, 403, 409))
def create_member(data: UserCreateRequest, db: DB, admin: Admin):
    user = service.create_user(
        db, organization_id=admin.organization_id,  # never from the request body
        name=data.name, email=data.email, password=data.password, role=data.role,
    )
    db.commit()
    AuditService.log_event(
        "USER_CREATED", f"{admin.email} created user {user.email} with role {user.role}.",
        {"role": user.role},
        organization_id=admin.organization_id, actor_user_id=admin.id, resource_type="USER", resource_id=user.id,
    )
    return user


@router.patch("/{user_id}", response_model=UserSummary,
              summary="Change a member's name, role, or active status (ADMIN)",
              responses=error_responses(400, 401, 403, 404))
def update_member(user_id: str, data: UserUpdateRequest, db: DB, admin: Admin):
    """Deactivating (`is_active: false`) is how users are removed; it revokes access immediately
    while keeping their audit history attributable."""
    target = service.get_user_in_organization(db, organization_id=admin.organization_id, user_id=user_id)
    changes = service.update_user(db, actor=admin, target=target, data=data)
    if changes:
        AuditService.log_event(
            "USER_UPDATED", f"{admin.email} updated user {target.email}.", {"changes": changes},
            organization_id=admin.organization_id, actor_user_id=admin.id, resource_type="USER", resource_id=target.id,
        )
    return target

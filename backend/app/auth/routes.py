from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.dependencies import CurrentUser
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.core.database import get_db
from app.core.errors import error_responses
from app.services.audit_service import AuditService
from app.users.schemas import CurrentUserResponse
from app.users.service import to_current_user_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

DB = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and its admin user",
    responses=error_responses(409),
)
def register(data: RegisterRequest, db: DB):
    """Creates a merchant organization and its first user (role ADMIN), and returns an access token."""
    return service.register(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange email and password for an access token",
    responses=error_responses(401, 403),
)
def login(data: LoginRequest, db: DB):
    """Returns a JWT bearer token. Send it as `Authorization: Bearer <token>` on subsequent requests."""
    return service.login(db, data)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="The authenticated user, their organization, and permissions",
    responses=error_responses(401),
)
def me(user: CurrentUser):
    return to_current_user_response(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a sign-out",
    responses=error_responses(401),
)
def logout(user: CurrentUser):
    """
    Access tokens are stateless, so the client signs out by discarding its token; this endpoint
    records the sign-out in the audit trail. The token remains technically valid until it
    expires (ACCESS_TOKEN_EXPIRE_MINUTES). Deactivating a user revokes access immediately.
    """
    AuditService.log_event(
        "USER_LOGOUT", f"{user.email} signed out.",
        organization_id=user.organization_id, actor_user_id=user.id,
        resource_type="USER", resource_id=user.id,
    )

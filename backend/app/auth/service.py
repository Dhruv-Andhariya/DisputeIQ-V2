import logging

from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.core.database import utcnow
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import create_access_token, verify_password
from app.organizations.service import create_organization
from app.services.audit_service import AuditService
from app.users import service as user_service
from app.users.models import Role, User

logger = logging.getLogger("disputeiq.auth")

INVALID_CREDENTIALS = "Invalid email or password."


def issue_token(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=user_service.to_current_user_response(user),
    )


def register(db: Session, data: RegisterRequest) -> TokenResponse:
    """Creates an organization and its first ADMIN in a single transaction."""
    org = create_organization(db, data.organization_name)
    user = user_service.create_user(
        db, organization_id=org.id, name=data.name, email=data.email,
        password=data.password, role=Role.ADMIN,
    )
    user.last_login_at = utcnow()
    db.commit()

    AuditService.log_event(
        "ORGANIZATION_REGISTERED",
        f"Organization '{org.name}' registered by {user.email}.",
        {"organization_slug": org.slug},
        organization_id=org.id, actor_user_id=user.id,
        resource_type="ORGANIZATION", resource_id=org.id,
    )
    logger.info("Organization registered org_id=%s user_id=%s", org.id, user.id)
    return issue_token(user)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = user_service.get_user_by_email(db, data.email)

    # verify_password runs even when the user doesn't exist, so response timing
    # doesn't reveal which emails are registered.
    if not verify_password(data.password, user.password_hash if user else None) or user is None:
        if user is not None:
            AuditService.log_event(
                "LOGIN_FAILED", "Failed login attempt (wrong password).",
                organization_id=user.organization_id, resource_type="USER", resource_id=user.id,
            )
        logger.warning("Failed login attempt for email=%s", data.email)
        raise AuthenticationError(INVALID_CREDENTIALS)

    if not user.is_active or not user.organization.is_active:
        logger.warning("Login attempt for disabled account user_id=%s", user.id)
        raise PermissionDeniedError("This account has been disabled. Contact your organization admin.")

    user.last_login_at = utcnow()
    db.commit()

    AuditService.log_event(
        "USER_LOGIN", f"{user.email} signed in.",
        organization_id=user.organization_id, actor_user_id=user.id,
        resource_type="USER", resource_id=user.id,
    )
    return issue_token(user)

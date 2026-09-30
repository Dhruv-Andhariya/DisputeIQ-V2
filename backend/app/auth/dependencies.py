"""
Authentication and authorization dependencies.

TENANT ISOLATION: the only trusted source of a request's organization is
`current_user.organization_id`, loaded from the database for the user in the JWT.
Routes must never accept an organization_id from the path, query, or body.
"""
from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.permissions import Permission, has_permission
from app.core.database import get_db
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.users.models import Role, User

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT access token. Obtain one from POST /auth/login or POST /auth/register.",
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated.")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise AuthenticationError("Invalid or expired token.")

    user = db.get(User, user_id)
    # A deactivated user (or organization) loses access immediately, even with an unexpired token.
    if user is None or not user.is_active or not user.organization.is_active:
        raise AuthenticationError("Invalid or expired token.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(*permissions: Permission) -> Callable[..., User]:
    """Dependency factory: the current user must hold every listed permission."""
    def dependency(user: CurrentUser) -> User:
        missing = [p for p in permissions if not has_permission(user.role, p)]
        if missing:
            raise PermissionDeniedError("You do not have permission to perform this action.")
        return user
    return dependency


def require_role(*roles: Role) -> Callable[..., User]:
    """Dependency factory: the current user must have one of the listed roles.
    Prefer require_permission; use this only when a rule is genuinely about the role itself."""
    allowed = {r.value for r in roles}

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError("You do not have permission to perform this action.")
        return user
    return dependency

from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.permissions import permissions_for
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.users.models import Role, User
from app.users.schemas import CurrentUserResponse, UserUpdateRequest


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).one_or_none()


def email_taken(db: Session, email: str) -> bool:
    return db.query(User.id).filter(User.email == email.lower()).first() is not None


def create_user(db: Session, *, organization_id: str, name: str, email: str, password: str, role: Role) -> User:
    """Adds a user to the session (caller commits). Emails are unique across all tenants."""
    if email_taken(db, email):
        raise ConflictError("A user with this email already exists.")
    user = User(
        organization_id=organization_id,
        name=name,
        email=email.lower(),
        password_hash=hash_password(password),
        role=role.value,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # concurrent request won the unique-email race
        db.rollback()
        raise ConflictError("A user with this email already exists.")
    return user


def list_users(db: Session, *, organization_id: str) -> List[User]:
    return (
        db.query(User)
        .filter(User.organization_id == organization_id)
        .order_by(User.created_at.asc())
        .all()
    )


def get_user_in_organization(db: Session, *, organization_id: str, user_id: str) -> User:
    """404 for users of other tenants, exactly as for users that don't exist."""
    user = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == organization_id)
        .one_or_none()
    )
    if user is None:
        raise NotFoundError("User not found.")
    return user


def update_user(db: Session, *, actor: User, target: User, data: UserUpdateRequest) -> dict:
    """Applies the update and returns {field: [old, new]} for the audit trail."""
    if target.id == actor.id and (
        (data.role is not None and data.role.value != actor.role)
        or data.is_active is False
    ):
        # Prevents an admin from locking the organization out of administration.
        raise BadRequestError("You cannot change your own role or deactivate your own account.")

    changes = {}
    if data.name is not None and data.name != target.name:
        changes["name"] = [target.name, data.name]
        target.name = data.name
    if data.role is not None and data.role.value != target.role:
        changes["role"] = [target.role, data.role.value]
        target.role = data.role.value
    if data.is_active is not None and data.is_active != target.is_active:
        changes["is_active"] = [target.is_active, data.is_active]
        target.is_active = data.is_active
    if changes:
        db.commit()
    return changes


def to_current_user_response(user: User) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate({
        **{k: getattr(user, k) for k in ("id", "name", "email", "role", "is_active", "created_at", "last_login_at")},
        "organization": user.organization,
        "permissions": sorted(p.value for p in permissions_for(user.role)),
    })

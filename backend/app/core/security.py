"""Password hashing (Argon2id) and JWT access tokens."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

# Verified against when the email is unknown, so a login for a nonexistent account
# costs the same time as a wrong password (prevents user enumeration via timing).
_DUMMY_HASH = _hasher.hash(uuid.uuid4().hex)

TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """
    Returns (token, expires_in_seconds).

    The token deliberately carries only the user id. Organization and role are always
    loaded from the database per request, so a role change or deactivation takes
    effect immediately and a client can never assert its own tenant.
    """
    expires_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> Optional[str]:
    """Returns the user id if the token is valid and unexpired, else None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        return None
    return payload.get("sub")

"""Application errors that map to clean HTTP responses (see handlers in app.main)."""
from pydantic import BaseModel


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class AuthenticationError(AppError):
    status_code = 401


class PermissionDeniedError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


# ---- OpenAPI documentation of error responses ----
class ErrorResponse(BaseModel):
    detail: str


def error_responses(*codes: int) -> dict:
    descriptions = {
        400: "Invalid request",
        401: "Not authenticated, or the token is invalid/expired",
        403: "Authenticated, but the role lacks the required permission",
        404: "Not found (also returned for resources owned by another organization)",
        409: "Conflict with existing data (e.g. duplicate email or slug)",
    }
    return {c: {"model": ErrorResponse, "description": descriptions[c]} for c in codes}

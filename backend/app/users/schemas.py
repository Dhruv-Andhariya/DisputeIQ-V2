from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.core.database import UTCDateTime
from app.users.models import Role

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
# Upper bound keeps password hashing cost bounded (DoS protection).
Password = Annotated[str, Field(min_length=8, max_length=128)]


class NormalizedEmailModel(BaseModel):
    @field_validator("email", mode="after", check_fields=False)
    @classmethod
    def _lowercase_email(cls, v):
        return v.lower() if isinstance(v, str) else v


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str


class UserSummary(BaseModel):
    """A user as seen by an organization admin. Never includes the password hash."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: Role
    is_active: bool
    created_at: UTCDateTime
    last_login_at: Optional[UTCDateTime] = None


class CurrentUserResponse(UserSummary):
    organization: OrganizationSummary
    permissions: List[str] = Field(description="Capabilities granted by the user's role")


class UserCreateRequest(NormalizedEmailModel):
    name: PersonName
    email: EmailStr
    password: Password
    role: Role = Role.VIEWER

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Priya Investigator",
        "email": "priya@abcelectronics.com",
        "password": "a-strong-password",
        "role": "INVESTIGATOR",
    }})


class UserUpdateRequest(BaseModel):
    name: Optional[PersonName] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None

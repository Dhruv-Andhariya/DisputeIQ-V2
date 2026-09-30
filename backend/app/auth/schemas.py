from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.organizations.schemas import OrganizationName
from app.users.schemas import CurrentUserResponse, NormalizedEmailModel, Password, PersonName


class RegisterRequest(NormalizedEmailModel):
    """Creates a new organization and its first user, who becomes its ADMIN."""
    organization_name: OrganizationName
    name: PersonName
    email: EmailStr
    password: Password

    model_config = ConfigDict(json_schema_extra={"example": {
        "organization_name": "ABC Electronics",
        "name": "Admin User",
        "email": "admin@abcelectronics.com",
        "password": "a-strong-password",
    }})


class LoginRequest(NormalizedEmailModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(json_schema_extra={"example": {
        "email": "admin@abcelectronics.com",
        "password": "a-strong-password",
    }})


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires")
    user: CurrentUserResponse

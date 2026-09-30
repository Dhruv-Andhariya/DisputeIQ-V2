from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.database import UTCDateTime
OrganizationName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=2, max_length=80,
                                        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime


class OrganizationUpdateRequest(BaseModel):
    name: Optional[OrganizationName] = None
    slug: Optional[Slug] = None

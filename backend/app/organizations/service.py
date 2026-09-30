import re
import secrets

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.organizations.models import Organization
from app.organizations.schemas import OrganizationUpdateRequest


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or "org"


def slug_taken(db: Session, slug: str) -> bool:
    return db.query(Organization.id).filter(Organization.slug == slug).first() is not None


def unique_slug(db: Session, name: str) -> str:
    """Two merchants may share a display name, so collisions get a short random suffix."""
    base = slugify(name)
    slug = base
    while slug_taken(db, slug):
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


def create_organization(db: Session, name: str) -> Organization:
    org = Organization(name=name, slug=unique_slug(db, name))
    db.add(org)
    db.flush()
    return org


def update_organization(db: Session, org: Organization, data: OrganizationUpdateRequest) -> dict:
    """Applies the update and returns {field: [old, new]} for the audit trail."""
    changes = {}
    if data.slug is not None and data.slug != org.slug:
        if slug_taken(db, data.slug):
            raise ConflictError("That organization slug is already in use.")
        changes["slug"] = [org.slug, data.slug]
        org.slug = data.slug
    if data.name is not None and data.name != org.name:
        changes["name"] = [org.name, data.name]
        org.name = data.name
    if changes:
        db.commit()
    return changes

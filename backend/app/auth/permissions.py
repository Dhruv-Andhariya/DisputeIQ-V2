"""
Role-based access control.

Routes check *permissions*, never role names, so adding a role or moving a capability
between roles is a one-line change here rather than an edit to every route.
"""
from enum import Enum
from typing import Dict, FrozenSet

from app.users.models import Role


class Permission(str, Enum):
    VIEW_CASES = "cases:view"                # disputes, evidence, timeline, investigation results, audit trail
    INVESTIGATE = "cases:investigate"        # run/re-run the investigation pipeline, record findings
    REVIEW_CASES = "cases:review"            # final human decision: approve contest / accept dispute
    MANAGE_USERS = "users:manage"
    MANAGE_ORGANIZATION = "organization:manage"
    VIEW_ORGANIZATION_AUDIT = "organization:audit"  # org-wide activity incl. logins and user changes


ROLE_PERMISSIONS: Dict[Role, FrozenSet[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.INVESTIGATOR: frozenset({Permission.VIEW_CASES, Permission.INVESTIGATE}),
    Role.ANALYST: frozenset({Permission.VIEW_CASES}),
    Role.VIEWER: frozenset({Permission.VIEW_CASES}),
}


def permissions_for(role: str) -> FrozenSet[Permission]:
    try:
        return ROLE_PERMISSIONS[Role(role)]
    except ValueError:
        return frozenset()


def has_permission(role: str, permission: Permission) -> bool:
    return permission in permissions_for(role)

"""
DisputeIQ management commands. Run from the repository root:

    python backend/manage.py migrate
    python backend/manage.py seed
    python backend/manage.py create-user --org demo-merchant --email admin@demo.local --name "Demo Admin" --role ADMIN
"""
import argparse
import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(BACKEND_DIR), str(BACKEND_DIR.parent)]  # `app` package, and `data`/`evaluation`


def cmd_migrate(_args):
    from app.core.migrations import upgrade_to_head
    upgrade_to_head()
    print("Database is at the latest schema revision.")


def cmd_seed(_args):
    from app.database.db import count_disputes, init_db
    from app.database.seed import seed_database
    init_db()
    if count_disputes() > 0:
        print("Database already contains disputes; skipping seed.")
        return
    seed_database()


def cmd_create_user(args):
    from pydantic import ValidationError
    from app.core.database import SessionLocal
    from app.core.errors import AppError
    from app.database.db import init_db
    from app.organizations.models import Organization
    from app.services.audit_service import AuditService
    from app.users.models import Role
    from app.users.schemas import UserCreateRequest
    from app.users.service import create_user

    init_db()
    password = args.password or getpass.getpass("Password (min 8 chars): ")
    try:
        data = UserCreateRequest(name=args.name, email=args.email, password=password, role=Role(args.role))
    except ValidationError as e:
        sys.exit(f"Invalid input: {e}")

    with SessionLocal() as db:
        org = db.query(Organization).filter(Organization.slug == args.org).one_or_none()
        if org is None:
            slugs = [s for (s,) in db.query(Organization.slug).all()]
            sys.exit(f"No organization with slug '{args.org}'. Existing: {', '.join(slugs) or 'none'}")
        try:
            user = create_user(db, organization_id=org.id, name=data.name, email=data.email,
                               password=data.password, role=data.role)
            db.commit()
        except AppError as e:
            sys.exit(e.detail)
        AuditService.log_event(
            "USER_CREATED", f"User {user.email} created with role {user.role} via management CLI.",
            {"role": user.role, "source": "cli"},
            organization_id=org.id, resource_type="USER", resource_id=user.id,
        )
        print(f"Created {user.role} {user.email} in organization '{org.name}' ({org.slug}).")


def cmd_seed_domain(_args):
    from app.database.db import init_db
    from app.domain.seed import seed_techflitter_domain

    init_db()
    created = seed_techflitter_domain()
    if created:
        print(f"Created {created} synthetic TechFlitter disputes with linked domain and evidence data.")
    else:
        print("TechFlitter demo data already exists; nothing was changed.")


def main():
    parser = argparse.ArgumentParser(description="DisputeIQ management commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Apply database migrations").set_defaults(func=cmd_migrate)
    sub.add_parser("seed", help="Load the synthetic demo dataset into the demo organization").set_defaults(func=cmd_seed)
    sub.add_parser("seed-domain", help="Load idempotent Phase 2/3 demo data into TechFlitter").set_defaults(func=cmd_seed_domain)

    p = sub.add_parser("create-user", help="Create a user in an existing organization")
    p.add_argument("--org", required=True, help="Organization slug, e.g. demo-merchant")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", default="ADMIN", choices=["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
    p.add_argument("--password", help="Omit to be prompted (keeps it out of shell history)")
    p.set_defaults(func=cmd_create_user)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

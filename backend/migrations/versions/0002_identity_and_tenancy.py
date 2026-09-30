"""Phase 1: organizations, users, and tenant scoping of legacy tables.

- Creates organizations and users.
- Adds organization_id to every tenant-owned legacy table.
- Extends audit_events with actor/resource attribution; dispute_id becomes nullable so
  non-dispute events (login, user management) can be audited too.
- Backfills pre-existing rows into a "Demo Merchant" organization so no data is lost.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match app.database.seed.DEMO_ORG_SLUG
DEMO_ORG_SLUG = "demo-merchant"
DEMO_ORG_NAME = "Demo Merchant"

TENANT_TABLES = ["disputes", "payments", "orders", "deliveries", "evidence", "investigations"]


def upgrade() -> None:
    organizations = op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # Legacy tables: nullable at the DB level because SQLite cannot add a NOT NULL column
    # to populated tables; the application layer always writes it. A real FK constraint
    # comes when these tables move onto the ORM.
    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("organization_id", sa.String(36), nullable=True))
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])

    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("dispute_id", existing_type=sa.Text, nullable=True)
        batch.add_column(sa.Column("organization_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("actor_user_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("resource_type", sa.String(40), nullable=True))
        batch.add_column(sa.Column("resource_id", sa.String(64), nullable=True))
        batch.create_index("ix_audit_events_organization_id", ["organization_id"])

    # ---- Backfill pre-existing data into the demo organization ----
    conn = op.get_bind()
    has_legacy_rows = any(
        conn.execute(sa.text(f"SELECT 1 FROM {t} LIMIT 1")).first() is not None
        for t in TENANT_TABLES + ["audit_events"]
    )
    if has_legacy_rows:
        org_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        op.bulk_insert(organizations, [{
            "id": org_id, "name": DEMO_ORG_NAME, "slug": DEMO_ORG_SLUG,
            "is_active": True, "created_at": now, "updated_at": now,
        }])
        for table in TENANT_TABLES + ["audit_events"]:
            conn.execute(
                sa.text(f"UPDATE {table} SET organization_id = :org WHERE organization_id IS NULL"),
                {"org": org_id},
            )

    conn.execute(sa.text(
        "UPDATE audit_events SET resource_type = 'DISPUTE', resource_id = dispute_id "
        "WHERE resource_type IS NULL AND dispute_id IS NOT NULL"
    ))


def downgrade() -> None:
    # Identity-only audit events (login etc.) have no dispute and cannot survive NOT NULL.
    op.execute("DELETE FROM audit_events WHERE dispute_id IS NULL")
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_index("ix_audit_events_organization_id")
        batch.drop_column("resource_id")
        batch.drop_column("resource_type")
        batch.drop_column("actor_user_id")
        batch.drop_column("organization_id")
        batch.alter_column("dispute_id", existing_type=sa.Text, nullable=False)

    for table in TENANT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_organization_id")
            batch.drop_column("organization_id")

    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")

"""Phase 2 merchant domain entities.

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_customer_id", sa.String(120), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "external_customer_id", name="uq_customers_org_external_id"),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])

    op.create_table(
        "merchant_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_order_id", sa.String(120), nullable=False),
        sa.Column("order_status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("order_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "external_order_id", name="uq_merchant_orders_org_external_id"),
    )
    op.create_index("ix_merchant_orders_organization_id", "merchant_orders", ["organization_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("merchant_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_transaction_id", sa.String(120), nullable=False),
        sa.Column("payment_method", sa.String(40), nullable=False, server_default="card"),
        sa.Column("transaction_status", sa.String(30), nullable=False, server_default="SUCCESS"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("transaction_type", sa.String(30), nullable=False, server_default="PAYMENT"),
        sa.Column("transaction_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "external_transaction_id", name="uq_transactions_org_external_id"),
    )
    op.create_index("ix_transactions_organization_id", "transactions", ["organization_id"])

    op.create_table(
        "domain_disputes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("merchant_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_dispute_id", sa.String(120), nullable=False),
        sa.Column("dispute_type", sa.String(40), nullable=False, server_default="PAYMENT_DISPUTE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("reason", sa.String(160), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("legacy_dispute_id", sa.String(120), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "external_dispute_id", name="uq_domain_disputes_org_external_id"),
    )
    op.create_index("ix_domain_disputes_organization_id", "domain_disputes", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_domain_disputes_organization_id", table_name="domain_disputes")
    op.drop_table("domain_disputes")
    op.drop_index("ix_transactions_organization_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_merchant_orders_organization_id", table_name="merchant_orders")
    op.drop_table("merchant_orders")
    op.drop_index("ix_customers_organization_id", table_name="customers")
    op.drop_table("customers")

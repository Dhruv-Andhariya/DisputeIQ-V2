"""Baseline: legacy dispute pipeline schema (pre-Phase 1).

Adopts databases created by the old CREATE TABLE IF NOT EXISTS bootstrap: tables that
already exist are left untouched, so existing data is preserved.

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _text(name, nullable=False):
    return sa.Column(name, sa.Text, nullable=nullable)


LEGACY_TABLES = {
    "disputes": lambda: [
        sa.Column("dispute_id", sa.Text, primary_key=True),
        _text("payment_id"), _text("merchant_id"),
        sa.Column("amount", sa.Float, nullable=False),
        _text("currency"), _text("reason"), _text("status"), _text("dispute_date"),
        _text("case_type"), _text("created_at"), _text("updated_at"),
    ],
    "payments": lambda: [
        sa.Column("payment_id", sa.Text, primary_key=True),
        _text("order_id"), _text("customer_id"),
        sa.Column("amount", sa.Float, nullable=False),
        _text("currency"), _text("status"), _text("method"), _text("created_at"),
    ],
    "orders": lambda: [
        sa.Column("order_id", sa.Text, primary_key=True),
        _text("customer_id"), _text("items"),
        sa.Column("total_amount", sa.Float, nullable=False),
        _text("currency"), _text("shipping_address"), _text("customer_email"),
        _text("customer_name"), _text("created_at"),
    ],
    "deliveries": lambda: [
        sa.Column("delivery_id", sa.Text, primary_key=True),
        _text("order_id"), _text("carrier"), _text("tracking_number"), _text("status"),
        _text("estimated_delivery_date"), _text("actual_delivery_date", True),
        _text("recipient_name", True), _text("signed_by", True),
        _text("delivery_address"), _text("created_at"),
    ],
    "evidence": lambda: [
        sa.Column("evidence_id", sa.Text, primary_key=True),
        _text("dispute_id"), _text("category"), _text("file_name"), _text("file_type"),
        _text("content"), _text("verification_status"), _text("created_at"),
    ],
    "investigations": lambda: [
        sa.Column("investigation_id", sa.Text, primary_key=True),
        _text("dispute_id"), _text("verification_results"), _text("readiness_score"),
        _text("timeline"), _text("ai_analysis", True), _text("decision"), _text("status"),
        _text("created_at"),
    ],
    "audit_events": lambda: [
        sa.Column("event_id", sa.Text, primary_key=True),
        _text("dispute_id"), _text("event_type"), _text("description"), _text("metadata"),
        _text("timestamp"),
    ],
}


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for name, columns in LEGACY_TABLES.items():
        if name not in existing:
            op.create_table(name, *columns())


def downgrade() -> None:
    for name in reversed(list(LEGACY_TABLES)):
        op.drop_table(name)

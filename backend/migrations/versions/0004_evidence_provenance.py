"""Phase 3 evidence metadata, provenance, and artifact references.

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dispute_id", sa.String(120), nullable=False),
        sa.Column("domain_dispute_id", sa.String(36), sa.ForeignKey("domain_disputes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("merchant_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_type", sa.String(40), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="READY"),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evidence_records_organization_id", "evidence_records", ["organization_id"])
    op.create_index("ix_evidence_records_dispute_id", "evidence_records", ["organization_id", "dispute_id"])
    op.create_index("ix_evidence_records_content_hash", "evidence_records", ["organization_id", "content_hash"])


def downgrade() -> None:
    op.drop_index("ix_evidence_records_content_hash", table_name="evidence_records")
    op.drop_index("ix_evidence_records_dispute_id", table_name="evidence_records")
    op.drop_index("ix_evidence_records_organization_id", table_name="evidence_records")
    op.drop_table("evidence_records")

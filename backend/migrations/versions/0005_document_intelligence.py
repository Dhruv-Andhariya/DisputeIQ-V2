"""Phase 4 document processing and extraction results.

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_processing",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidence_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("processor", sa.String(60), nullable=False),
        sa.Column("processor_version", sa.String(80), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("classification_confidence", sa.Float, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PROCESSING"),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("page_data_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("structured_data_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("confidence_metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("extraction_schema", sa.String(80), nullable=False, server_default="generic.v1"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_processing_organization_id", "document_processing", ["organization_id"])
    op.create_index("ix_document_processing_evidence_id", "document_processing", ["organization_id", "evidence_id"])


def downgrade() -> None:
    op.drop_index("ix_document_processing_evidence_id", table_name="document_processing")
    op.drop_index("ix_document_processing_organization_id", table_name="document_processing")
    op.drop_table("document_processing")

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class DocumentProcessing(Base):
    __tablename__ = "document_processing"
    __table_args__ = (
        Index("ix_document_processing_organization_id", "organization_id"),
        Index("ix_document_processing_evidence_id", "organization_id", "evidence_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_records.id", ondelete="CASCADE"), nullable=False)
    processor: Mapped[str] = mapped_column(String(60), nullable=False)
    processor_version: Mapped[str] = mapped_column(String(80), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    classification_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PROCESSING")
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_data_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    structured_data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    confidence_metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    extraction_schema: Mapped[str] = mapped_column(String(80), nullable=False, default="generic.v1")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

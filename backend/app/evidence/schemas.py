from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


EVIDENCE_TYPES = {
    "PAYMENT_RECEIPT", "INVOICE", "ORDER_RECORD", "TRANSACTION_RECORD",
    "SHIPPING_DOCUMENT", "DELIVERY_PROOF", "REFUND_RECORD", "CANCELLATION_RECORD",
    "CUSTOMER_COMMUNICATION", "IDENTITY_DOCUMENT", "SCREENSHOT", "OTHER",
}
SOURCE_TYPES = {"MERCHANT_UPLOAD", "CUSTOMER_UPLOAD", "SYSTEM_GENERATED", "API_IMPORT", "EXTERNAL_INTEGRATION"}
EVIDENCE_STATUSES = {"UPLOADED", "STORED", "READY", "ARCHIVED", "DELETED", "FAILED"}


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    dispute_id: str
    domain_dispute_id: Optional[str]
    customer_id: Optional[str]
    order_id: Optional[str]
    transaction_id: Optional[str]
    evidence_type: str
    source_type: str
    original_filename: str
    mime_type: str
    file_size: int
    content_hash: str
    uploaded_by_user_id: str
    uploaded_at: datetime
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EvidenceUpdate(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(default=None, max_length=20)

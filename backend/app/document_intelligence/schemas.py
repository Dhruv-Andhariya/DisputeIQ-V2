from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OCRBlock(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: Optional[List[float]] = None
    page: int = Field(ge=1)


class OCRPage(BaseModel):
    page: int = Field(ge=1)
    blocks: List[OCRBlock]


class InvoiceExtraction(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    customer_name: Optional[str] = None
    merchant_name: Optional[str] = None
    order_id: Optional[str] = None
    transaction_id: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None


class PaymentReceiptExtraction(BaseModel):
    transaction_id: Optional[str] = None
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    customer: Optional[str] = None
    status: Optional[str] = None


class DeliveryProofExtraction(BaseModel):
    order_id: Optional[str] = None
    delivery_date: Optional[str] = None
    recipient_name: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_status: Optional[str] = None
    tracking_id: Optional[str] = None


class RefundExtraction(BaseModel):
    refund_id: Optional[str] = None
    transaction_id: Optional[str] = None
    refund_date: Optional[str] = None
    refund_amount: Optional[float] = None
    currency: Optional[str] = None
    refund_status: Optional[str] = None


class GenericExtraction(BaseModel):
    fields: Dict[str, Any] = {}


class ProcessingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    evidence_id: str
    processor: str
    processor_version: str
    document_type: str
    classification_confidence: Optional[float]
    status: str
    raw_text: Optional[str]
    pages: List[OCRPage]
    structured_data: Dict[str, Any]
    confidence_metadata: Dict[str, Any]
    extraction_schema: str
    error_message: Optional[str]
    attempt_count: int
    created_at: datetime
    updated_at: datetime

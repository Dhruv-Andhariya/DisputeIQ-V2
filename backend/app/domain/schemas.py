from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    external_customer_id: Optional[str] = Field(default=None, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)


class CustomerResponse(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class OrderCreate(BaseModel):
    customer_id: str
    external_order_id: str = Field(min_length=1, max_length=120)
    order_status: str = Field(default="CREATED", max_length=30)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    total_amount: float = Field(gt=0)
    order_created_at: datetime


class OrderUpdate(BaseModel):
    order_status: Optional[str] = Field(default=None, max_length=30)


class OrderResponse(OrderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    customer: CustomerResponse


class TransactionCreate(BaseModel):
    order_id: str
    external_transaction_id: str = Field(min_length=1, max_length=120)
    payment_method: str = Field(default="card", max_length=40)
    transaction_status: str = Field(default="SUCCESS", max_length=30)
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    transaction_type: str = Field(default="PAYMENT", max_length=30)
    transaction_timestamp: datetime


class TransactionResponse(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    order: OrderResponse


class DisputeCreate(BaseModel):
    customer_id: str
    order_id: str
    transaction_id: str
    external_dispute_id: str = Field(min_length=1, max_length=120)
    dispute_type: str = Field(default="PAYMENT_DISPUTE", max_length=40)
    reason: str = Field(min_length=1, max_length=160)
    description: Optional[str] = None
    opened_at: datetime


class DisputeUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=30)
    description: Optional[str] = None


class DomainDisputeResponse(DisputeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    status: str
    legacy_dispute_id: str
    created_at: datetime
    updated_at: datetime
    customer: CustomerResponse
    order: OrderResponse
    transaction: TransactionResponse

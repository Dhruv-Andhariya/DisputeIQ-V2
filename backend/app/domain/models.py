import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_customer_id", name="uq_customers_org_external_id"),
        Index("ix_customers_organization_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    external_customer_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class MerchantOrder(Base):
    __tablename__ = "merchant_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_order_id", name="uq_merchant_orders_org_external_id"),
        Index("ix_merchant_orders_organization_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(120), nullable=False)
    order_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    order_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    customer: Mapped[Customer] = relationship(lazy="joined")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_transaction_id", name="uq_transactions_org_external_id"),
        Index("ix_transactions_organization_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("merchant_orders.id", ondelete="RESTRICT"), nullable=False)
    external_transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="card")
    transaction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUCCESS")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False, default="PAYMENT")
    transaction_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    order: Mapped[MerchantOrder] = relationship(lazy="joined")


class DomainDispute(Base):
    __tablename__ = "domain_disputes"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_dispute_id", name="uq_domain_disputes_org_external_id"),
        Index("ix_domain_disputes_organization_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("merchant_orders.id", ondelete="RESTRICT"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False)
    external_dispute_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dispute_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PAYMENT_DISPUTE")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    legacy_dispute_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    customer: Mapped[Customer] = relationship(lazy="joined")
    order: Mapped[MerchantOrder] = relationship(lazy="joined")
    transaction: Mapped[Transaction] = relationship(lazy="joined")

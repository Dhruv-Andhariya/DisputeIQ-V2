from datetime import datetime
from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.database.db import save_dispute, save_order, save_payment
from app.models.domain import Dispute, DisputeReason
from app.services.audit_service import AuditService
from app.domain.models import Customer, DomainDispute, MerchantOrder, Transaction
from app.domain.schemas import CustomerCreate, CustomerUpdate, DisputeCreate, DisputeUpdate, OrderCreate, OrderUpdate, TransactionCreate


def _legacy_id(organization_id: str, external_id: str) -> str:
    """Keep compatibility-table primary keys unique without changing merchant IDs."""
    return f"{organization_id[:8]}-{external_id}"


def _one_or_404(db: Session, model: Type, value: str, organization_id: str, label: str):
    item = db.scalar(select(model).where(model.id == value, model.organization_id == organization_id))
    if item is None:
        raise NotFoundError(f"{label} not found.")
    return item


def _commit(db: Session, organization_id: str, event: str, description: str, actor_user_id: str, resource_type: str, resource_id: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A record with the same external ID already exists in this organization.") from exc
    AuditService.log_event(event, description, organization_id=organization_id, actor_user_id=actor_user_id,
                           resource_type=resource_type, resource_id=resource_id)


def _commit_db(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A record with the same external ID already exists in this organization.") from exc


def _audit(organization_id: str, event: str, description: str, actor_user_id: str, resource_type: str, resource_id: str):
    AuditService.log_event(event, description, organization_id=organization_id, actor_user_id=actor_user_id,
                           resource_type=resource_type, resource_id=resource_id)


def list_customers(db: Session, organization_id: str):
    return db.scalars(select(Customer).where(Customer.organization_id == organization_id).order_by(Customer.created_at.desc())).all()


def get_customer(db: Session, customer_id: str, organization_id: str):
    return _one_or_404(db, Customer, customer_id, organization_id, "Customer")


def create_customer(db: Session, data: CustomerCreate, organization_id: str, actor_user_id: str):
    item = Customer(**data.model_dump(), organization_id=organization_id)
    db.add(item)
    db.flush()
    _commit(db, organization_id, "CUSTOMER_CREATED", f"Customer '{item.name}' created.", actor_user_id, "CUSTOMER", item.id)
    return item


def update_customer(db: Session, customer_id: str, data: CustomerUpdate, organization_id: str, actor_user_id: str):
    item = get_customer(db, customer_id, organization_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.flush()
    _commit(db, organization_id, "CUSTOMER_UPDATED", f"Customer '{item.name}' updated.", actor_user_id, "CUSTOMER", item.id)
    return item


def list_orders(db: Session, organization_id: str):
    return db.scalars(select(MerchantOrder).where(MerchantOrder.organization_id == organization_id).order_by(MerchantOrder.created_at.desc())).all()


def get_order(db: Session, order_id: str, organization_id: str):
    return _one_or_404(db, MerchantOrder, order_id, organization_id, "Order")


def create_order(db: Session, data: OrderCreate, organization_id: str, actor_user_id: str):
    customer = get_customer(db, data.customer_id, organization_id)
    item = MerchantOrder(**data.model_dump(), organization_id=organization_id)
    db.add(item)
    db.flush()
    _commit_db(db)
    save_order(__import__("app.models.domain", fromlist=["Order"]).Order(
        order_id=_legacy_id(organization_id, item.external_order_id), customer_id=customer.external_customer_id or customer.id,
        items=[], total_amount=item.total_amount, currency=item.currency, shipping_address="",
        customer_email=customer.email or "", customer_name=customer.name,
        created_at=item.order_created_at.strftime("%Y-%m-%d %H:%M:%S"), organization_id=organization_id,
    ))
    _audit(organization_id, "ORDER_CREATED", f"Order '{item.external_order_id}' created.", actor_user_id, "ORDER", item.id)
    return item


def update_order(db: Session, order_id: str, data: OrderUpdate, organization_id: str, actor_user_id: str):
    item = get_order(db, order_id, organization_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.flush()
    _commit(db, organization_id, "ORDER_UPDATED", f"Order '{item.external_order_id}' updated.", actor_user_id, "ORDER", item.id)
    return item


def list_transactions(db: Session, organization_id: str):
    return db.scalars(select(Transaction).where(Transaction.organization_id == organization_id).order_by(Transaction.created_at.desc())).all()


def get_transaction(db: Session, transaction_id: str, organization_id: str):
    return _one_or_404(db, Transaction, transaction_id, organization_id, "Transaction")


def create_transaction(db: Session, data: TransactionCreate, organization_id: str, actor_user_id: str):
    order = get_order(db, data.order_id, organization_id)
    item = Transaction(**data.model_dump(), organization_id=organization_id)
    db.add(item)
    db.flush()
    _commit_db(db)
    save_payment(__import__("app.models.domain", fromlist=["Payment"]).Payment(
        payment_id=_legacy_id(organization_id, item.external_transaction_id), order_id=_legacy_id(organization_id, order.external_order_id),
        customer_id=order.customer.external_customer_id or order.customer.id, amount=item.amount,
        currency=item.currency, status=item.transaction_status.lower(), method=item.payment_method,
        created_at=item.transaction_timestamp.strftime("%Y-%m-%d %H:%M:%S"), organization_id=organization_id,
    ))
    _audit(organization_id, "TRANSACTION_CREATED", f"Transaction '{item.external_transaction_id}' created.", actor_user_id, "TRANSACTION", item.id)
    return item


def list_disputes(db: Session, organization_id: str):
    return db.scalars(select(DomainDispute).where(DomainDispute.organization_id == organization_id).order_by(DomainDispute.created_at.desc())).all()


def get_dispute(db: Session, dispute_id: str, organization_id: str):
    item = db.scalar(select(DomainDispute).where(DomainDispute.id == dispute_id, DomainDispute.organization_id == organization_id))
    if item is None:
        item = db.scalar(select(DomainDispute).where(DomainDispute.external_dispute_id == dispute_id, DomainDispute.organization_id == organization_id))
    if item is None:
        item = db.scalar(select(DomainDispute).where(DomainDispute.legacy_dispute_id == dispute_id, DomainDispute.organization_id == organization_id))
    if item is None:
        raise NotFoundError("Dispute not found.")
    return item


def create_dispute(db: Session, data: DisputeCreate, organization_id: str, actor_user_id: str):
    customer = get_customer(db, data.customer_id, organization_id)
    order = get_order(db, data.order_id, organization_id)
    transaction = get_transaction(db, data.transaction_id, organization_id)
    if transaction.order_id != order.id or order.customer_id != customer.id:
        raise ConflictError("Customer, order, and transaction relationships are inconsistent.")
    item = DomainDispute(**data.model_dump(), organization_id=organization_id,
                         legacy_dispute_id=_legacy_id(organization_id, data.external_dispute_id))
    db.add(item)
    db.flush()
    _commit_db(db)
    save_dispute(Dispute(
        dispute_id=item.legacy_dispute_id, payment_id=_legacy_id(organization_id, transaction.external_transaction_id),
        merchant_id=organization_id, amount=transaction.amount, currency=transaction.currency,
        reason=DisputeReason.GOODS_SERVICES_NOT_RECEIVED, dispute_date=item.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
        created_at=item.opened_at.strftime("%Y-%m-%d %H:%M:%S"), updated_at=item.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
        organization_id=organization_id,
    ))
    _audit(organization_id, "DISPUTE_CREATED", f"Dispute '{item.external_dispute_id}' created.", actor_user_id, "DISPUTE", item.id)
    return item


def update_dispute(db: Session, dispute_id: str, data: DisputeUpdate, organization_id: str, actor_user_id: str):
    item = get_dispute(db, dispute_id, organization_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_at = datetime.utcnow()
    db.flush()
    _commit(db, organization_id, "DISPUTE_UPDATED", f"Dispute '{item.external_dispute_id}' updated.", actor_user_id, "DISPUTE", item.id)
    return item

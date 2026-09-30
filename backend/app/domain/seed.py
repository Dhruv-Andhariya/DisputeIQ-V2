"""Idempotent synthetic Phase 2/3 data for the TechFlitter organization."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.database.db import save_delivery, save_dispute, save_evidence, save_order, save_payment
from app.domain.models import Customer, DomainDispute, MerchantOrder, Transaction
from app.domain.service import _legacy_id
from app.evidence.models import EvidenceRecord
from app.evidence.storage import storage
from app.models.domain import Delivery, Dispute, Evidence, EvidenceCategory, Order, OrderItem, Payment
from app.services.audit_service import AuditService

TECHFLITTER_SLUG = "techflitter"
SEED_MARKER = "TECHFLITTER-DEMO"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _admin_id(db, organization_id: str) -> str:
    from app.users.models import Role, User
    user = db.scalar(select(User).where(User.organization_id == organization_id, User.role == Role.ADMIN.value).order_by(User.created_at))
    if user is None:
        raise ValueError("TechFlitter needs an ADMIN user before demo evidence can be seeded.")
    return user.id


def seed_techflitter_domain() -> int:
    from app.organizations.models import Organization

    with SessionLocal() as db:
        organization = db.scalar(select(Organization).where(Organization.slug == TECHFLITTER_SLUG))
        if organization is None:
            raise ValueError("Organization 'techflitter' does not exist. Register it first.")
        marker = f"{SEED_MARKER}-CUSTOMER-001"
        if db.scalar(select(Customer).where(Customer.organization_id == organization.id, Customer.external_customer_id == marker)):
            return 0

        now = _dt("2026-09-29T12:00:00")
        customer_specs = [
            ("Aarav Mehta", "aarav@techflitter.demo", "+91-9000000001"),
            ("Diya Shah", "diya@techflitter.demo", "+91-9000000002"),
            ("Kabir Nair", "kabir@techflitter.demo", "+91-9000000003"),
            ("Myra Iyer", "myra@techflitter.demo", "+91-9000000004"),
            ("Vivaan Rao", "vivaan@techflitter.demo", "+91-9000000005"),
        ]
        customers = []
        for index, (name, email, phone) in enumerate(customer_specs, 1):
            customer = Customer(
                organization_id=organization.id,
                external_customer_id=f"{SEED_MARKER}-CUSTOMER-{index:03d}",
                name=name, email=email, phone=phone, created_at=now, updated_at=now,
            )
            db.add(customer)
            customers.append(customer)
        db.flush()

        amounts = [2499, 4999, 1299, 7999, 1999]
        orders = []
        for index, customer in enumerate(customers, 1):
            order = MerchantOrder(
                organization_id=organization.id, customer_id=customer.id,
                external_order_id=f"{SEED_MARKER}-ORDER-{index:03d}",
                order_status=["PAID", "SHIPPED", "DELIVERED", "REFUNDED", "CANCELLED"][index - 1],
                currency="INR", total_amount=amounts[index - 1],
                order_created_at=_dt(f"2026-09-{10 + index:02d}T10:00:00"),
                created_at=now, updated_at=now,
            )
            db.add(order)
            orders.append(order)
        db.flush()

        transactions = []
        for index, order in enumerate(orders, 1):
            transaction = Transaction(
                organization_id=organization.id, order_id=order.id,
                external_transaction_id=f"{SEED_MARKER}-TXN-{index:03d}",
                payment_method=["card", "upi", "netbanking", "card", "wallet"][index - 1],
                transaction_status=["SUCCESS", "SUCCESS", "REFUNDED", "SUCCESS", "REVERSED"][index - 1],
                amount=order.total_amount, currency="INR",
                transaction_type=["PAYMENT", "PAYMENT", "REFUND", "PAYMENT", "REVERSAL"][index - 1],
                transaction_timestamp=order.order_created_at, created_at=now, updated_at=now,
            )
            db.add(transaction)
            transactions.append(transaction)
        db.flush()

        dispute_specs = [
            ("PAYMENT_DISPUTE", "Customer does not recognize the card payment.", "OPEN"),
            ("DUPLICATE_PAYMENT", "Customer reports a duplicate payment.", "UNDER_REVIEW"),
            ("REFUND_DISPUTE", "Expected refund has not arrived.", "INVESTIGATING"),
            ("CANCELLATION_DISPUTE", "Cancelled order was still charged.", "AWAITING_REVIEW"),
            ("DELIVERY_DISPUTE", "Customer reports the order was not delivered.", "RESOLVED"),
        ]
        disputes = []
        for index, (dispute_type, reason, status) in enumerate(dispute_specs, 1):
            external_id = f"{SEED_MARKER}-DISPUTE-{index:03d}"
            dispute = DomainDispute(
                organization_id=organization.id, customer_id=customers[index - 1].id,
                order_id=orders[index - 1].id, transaction_id=transactions[index - 1].id,
                external_dispute_id=external_id, dispute_type=dispute_type, status=status,
                reason=reason, description=f"Synthetic TechFlitter demonstration case {index}.",
                opened_at=_dt(f"2026-09-{20 + index:02d}T14:00:00"),
                legacy_dispute_id=_legacy_id(organization.id, external_id),
                created_at=now, updated_at=now,
            )
            db.add(dispute)
            disputes.append(dispute)
        db.commit()

        admin_id = _admin_id(db, organization.id)
        for index, (customer, order, transaction, dispute) in enumerate(zip(customers, orders, transactions, disputes), 1):
            legacy_order_id = _legacy_id(organization.id, order.external_order_id)
            legacy_transaction_id = _legacy_id(organization.id, transaction.external_transaction_id)
            created_at = order.order_created_at.strftime("%Y-%m-%d %H:%M:%S")
            save_order(Order(
                order_id=legacy_order_id, customer_id=customer.external_customer_id,
                items=[OrderItem(item_id=f"{SEED_MARKER}-ITEM-{index:03d}", name="TechFlitter Demo Device", quantity=1, price=float(order.total_amount))],
                total_amount=float(order.total_amount), currency="INR", shipping_address="Synthetic TechFlitter address",
                customer_email=customer.email, customer_name=customer.name, created_at=created_at,
                organization_id=organization.id,
            ))
            save_payment(Payment(
                payment_id=legacy_transaction_id, order_id=legacy_order_id, customer_id=customer.external_customer_id,
                amount=float(transaction.amount), currency="INR", status=transaction.transaction_status.lower(),
                method=transaction.payment_method, created_at=created_at, organization_id=organization.id,
            ))
            save_delivery(Delivery(
                delivery_id=_legacy_id(organization.id, f"{SEED_MARKER}-DELIVERY-{index:03d}"), order_id=legacy_order_id,
                carrier="TechFlitter Demo Logistics", tracking_number=f"TFDEMO{index:06d}",
                status="DELIVERED" if index != 4 else "IN_TRANSIT", estimated_delivery_date="2026-09-25",
                actual_delivery_date="2026-09-24 16:00:00" if index != 4 else None, recipient_name=customer.name,
                signed_by=customer.name if index != 4 else None, delivery_address="Synthetic TechFlitter address",
                created_at=created_at, organization_id=organization.id,
            ))
            save_dispute(Dispute(
                dispute_id=dispute.legacy_dispute_id, payment_id=legacy_transaction_id, merchant_id=organization.id,
                amount=float(transaction.amount), currency="INR", dispute_date=dispute.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
                created_at=created_at, updated_at=now.strftime("%Y-%m-%d %H:%M:%S"), organization_id=organization.id,
            ))

        evidence_specs = [
            ("PAYMENT_RECEIPT", "MERCHANT_UPLOAD", "payment_receipt.json", {"transaction_id": transactions[0].external_transaction_id}),
            ("INVOICE", "SYSTEM_GENERATED", "invoice.json", {"order_id": orders[1].external_order_id, "amount": float(orders[1].total_amount)}),
            ("DELIVERY_PROOF", "API_IMPORT", "delivery_proof.json", {"tracking_number": "TFDEMO000003", "status": "DELIVERED"}),
            ("CUSTOMER_COMMUNICATION", "CUSTOMER_UPLOAD", "customer_message.json", {"message": "I am following up on my dispute."}),
            ("REFUND_RECORD", "EXTERNAL_INTEGRATION", "refund_record.json", {"transaction_id": transactions[2].external_transaction_id, "status": "REFUNDED"}),
        ]
        legacy_evidence = []
        legacy_categories = {
            "PAYMENT_RECEIPT": EvidenceCategory.INVOICE, "INVOICE": EvidenceCategory.INVOICE,
            "DELIVERY_PROOF": EvidenceCategory.PROOF_OF_DELIVERY,
            "CUSTOMER_COMMUNICATION": EvidenceCategory.CUSTOMER_COMMUNICATION,
            "REFUND_RECORD": EvidenceCategory.TERMS_AND_CONDITIONS,
        }
        for index, (evidence_type, source_type, filename, payload) in enumerate(evidence_specs):
            dispute = disputes[index]
            content = json.dumps(payload, indent=2).encode("utf-8")
            evidence_id = str(uuid.uuid4())
            storage_key = storage.key_for(organization.id, dispute.legacy_dispute_id, evidence_id)
            storage.write(storage_key, content)
            record = EvidenceRecord(
                id=evidence_id, organization_id=organization.id, dispute_id=dispute.legacy_dispute_id,
                domain_dispute_id=dispute.id, customer_id=dispute.customer_id, order_id=dispute.order_id,
                transaction_id=dispute.transaction_id, evidence_type=evidence_type, source_type=source_type,
                original_filename=filename, mime_type="application/json", file_size=len(content), storage_key=storage_key,
                content_hash=hashlib.sha256(content).hexdigest(), uploaded_by_user_id=admin_id, uploaded_at=now,
                status="READY", metadata_json=json.dumps({"seed": SEED_MARKER}), created_at=now, updated_at=now,
            )
            db.add(record)
            legacy_evidence.append(Evidence(
                evidence_id=f"EVD-{evidence_id}", dispute_id=dispute.legacy_dispute_id,
                category=legacy_categories[evidence_type], file_name=filename, file_type="application/json",
                content={"phase3_evidence_id": evidence_id, **payload}, created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
                organization_id=organization.id,
            ))
        db.commit()
        for item in legacy_evidence:
            save_evidence(item)
        for dispute in disputes:
            AuditService.log_event(
                "DISPUTE_RECEIVED", f"Synthetic TechFlitter dispute '{dispute.external_dispute_id}' seeded.",
                {"seed": SEED_MARKER, "dispute_type": dispute.dispute_type}, organization_id=organization.id,
                resource_type="DISPUTE", resource_id=dispute.id,
            )
        return len(disputes)

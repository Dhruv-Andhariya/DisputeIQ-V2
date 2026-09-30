import json
from app.core.config import BASE_DIR
from app.core.database import SessionLocal
from app.database.db import (
    init_db, save_dispute, save_payment, save_order, save_delivery, save_evidence, save_audit_event
)
from app.models.domain import Dispute, Payment, Order, Delivery, Evidence, AuditEvent
from app.organizations.models import Organization

# Must match migrations/versions/0002 (which backfills pre-existing data into this org)
DEMO_ORG_SLUG = "demo-merchant"
DEMO_ORG_NAME = "Demo Merchant"


def get_or_create_demo_organization() -> Organization:
    with SessionLocal() as db:
        org = db.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).one_or_none()
        if org is None:
            org = Organization(name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG)
            db.add(org)
            db.commit()
        return org


def seed_database():
    print("Applying database migrations...")
    init_db()

    dataset_path = BASE_DIR / "data" / "synthetic" / "dataset.json"
    if not dataset_path.exists():
        print("Synthetic dataset not found. Generating now...")
        from data.synthetic.generator import generate_synthetic_dataset
        generate_synthetic_dataset()

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    org = get_or_create_demo_organization()
    org_id = org.id
    print(f"Seeding {len(dataset)} dispute cases into organization '{org.name}' ({org.slug})...")

    for case in dataset:
        dispute = Dispute(**case["dispute"], organization_id=org_id)
        payment = Payment(**case["payment"], organization_id=org_id)
        order = Order(**case["order"], organization_id=org_id)
        delivery = Delivery(**case["delivery"], organization_id=org_id)

        save_dispute(dispute)
        save_payment(payment)
        save_order(order)
        save_delivery(delivery)

        for ev_data in case["evidence"]:
            evidence = Evidence(**ev_data, organization_id=org_id)
            save_evidence(evidence)

        # Initial Audit Event (system-initiated: no actor)
        audit = AuditEvent(
            event_id=f"AUD-{dispute.dispute_id}-INIT",
            dispute_id=dispute.dispute_id,
            event_type="DISPUTE_RECEIVED",
            description=f"Dispute received from payment infrastructure for amount ₹{dispute.amount}.",
            metadata={
                "merchant_id": dispute.merchant_id,
                "reason": dispute.reason,
                "case_type": dispute.case_type
            },
            timestamp=dispute.created_at,
            organization_id=org_id,
            resource_type="DISPUTE",
            resource_id=dispute.dispute_id,
        )
        save_audit_event(audit)

    print("Database seeding completed successfully!")

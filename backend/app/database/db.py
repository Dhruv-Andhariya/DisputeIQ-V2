"""
Persistence for the dispute pipeline (raw sqlite3).

TENANT ISOLATION RULES
- Every read of tenant-owned data takes a keyword-only `organization_id` and filters on it.
  There is deliberately no unscoped variant: forgetting the filter is a TypeError, not a data leak.
- Every write requires the record to carry an organization_id. The INSERT OR REPLACE upserts
  would otherwise silently orphan a row from its tenant.
- organization_id always comes from the authenticated user on the server, never from the client.

Schema is owned by Alembic (backend/migrations); init_db() just brings it to head.
"""
import sqlite3
import json
import os
from typing import List, Optional
from app.core.config import settings
from app.models.domain import (
    Dispute, Payment, Order, Delivery, Evidence, Investigation, AuditEvent,
    DisputeStatus
)

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")


def get_db_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Applies all pending schema migrations."""
    from app.core.migrations import upgrade_to_head
    upgrade_to_head()


def _require_org(record) -> str:
    if not record.organization_id:
        raise ValueError(f"{type(record).__name__} cannot be saved without an organization_id.")
    return record.organization_id


# Database Access Functions

def save_dispute(dispute: Dispute):
    org_id = _require_org(dispute)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO disputes
    (dispute_id, payment_id, merchant_id, amount, currency, reason, status, dispute_date, case_type, created_at, updated_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dispute.dispute_id, dispute.payment_id, dispute.merchant_id, dispute.amount,
        dispute.currency, dispute.reason, dispute.status, dispute.dispute_date,
        dispute.case_type, dispute.created_at, dispute.updated_at, org_id
    ))
    conn.commit()
    conn.close()

def get_dispute_by_id(dispute_id: str, *, organization_id: str) -> Optional[Dispute]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM disputes WHERE dispute_id = ? AND organization_id = ?",
        (dispute_id, organization_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return Dispute(**dict(row))
    return None

def get_all_disputes(*, organization_id: str) -> List[Dispute]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM disputes WHERE organization_id = ? ORDER BY created_at DESC",
        (organization_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [Dispute(**dict(r)) for r in rows]

def count_disputes() -> int:
    """Total across all tenants. Only used to decide whether to seed demo data."""
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM disputes").fetchone()[0]
    conn.close()
    return count

def save_payment(payment: Payment):
    org_id = _require_org(payment)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO payments
    (payment_id, order_id, customer_id, amount, currency, status, method, created_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payment.payment_id, payment.order_id, payment.customer_id, payment.amount,
        payment.currency, payment.status, payment.method, payment.created_at, org_id
    ))
    conn.commit()
    conn.close()

def get_payment_by_id(payment_id: str, *, organization_id: str) -> Optional[Payment]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM payments WHERE payment_id = ? AND organization_id = ?",
        (payment_id, organization_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return Payment(**dict(row))
    return None

def save_order(order: Order):
    org_id = _require_org(order)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO orders
    (order_id, customer_id, items, total_amount, currency, shipping_address, customer_email, customer_name, created_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order.order_id, order.customer_id, json.dumps([item.model_dump() for item in order.items]),
        order.total_amount, order.currency, order.shipping_address,
        order.customer_email, order.customer_name, order.created_at, org_id
    ))
    conn.commit()
    conn.close()

def get_order_by_id(order_id: str, *, organization_id: str) -> Optional[Order]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE order_id = ? AND organization_id = ?",
        (order_id, organization_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data['items'] = json.loads(data['items'])
        return Order(**data)
    return None

def save_delivery(delivery: Delivery):
    org_id = _require_org(delivery)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO deliveries
    (delivery_id, order_id, carrier, tracking_number, status, estimated_delivery_date, actual_delivery_date, recipient_name, signed_by, delivery_address, created_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        delivery.delivery_id, delivery.order_id, delivery.carrier, delivery.tracking_number,
        delivery.status, delivery.estimated_delivery_date, delivery.actual_delivery_date,
        delivery.recipient_name, delivery.signed_by, delivery.delivery_address, delivery.created_at, org_id
    ))
    conn.commit()
    conn.close()

def get_delivery_by_order_id(order_id: str, *, organization_id: str) -> Optional[Delivery]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM deliveries WHERE order_id = ? AND organization_id = ?",
        (order_id, organization_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return Delivery(**dict(row))
    return None

def save_evidence(evidence: Evidence):
    org_id = _require_org(evidence)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO evidence
    (evidence_id, dispute_id, category, file_name, file_type, content, verification_status, created_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        evidence.evidence_id, evidence.dispute_id, evidence.category, evidence.file_name,
        evidence.file_type, json.dumps(evidence.content), evidence.verification_status, evidence.created_at, org_id
    ))
    conn.commit()
    conn.close()

def get_evidence_by_dispute_id(dispute_id: str, *, organization_id: str) -> List[Evidence]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM evidence WHERE dispute_id = ? AND organization_id = ?",
        (dispute_id, organization_id),
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d['content'] = json.loads(d['content'])
        results.append(Evidence(**d))
    return results

def save_investigation(investigation: Investigation):
    org_id = _require_org(investigation)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO investigations
    (investigation_id, dispute_id, verification_results, readiness_score, timeline, ai_analysis, decision, status, created_at, organization_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        investigation.investigation_id, investigation.dispute_id,
        json.dumps([v.model_dump() for v in investigation.verification_results]),
        json.dumps(investigation.readiness_score.model_dump()),
        json.dumps([t.model_dump() for t in investigation.timeline]),
        json.dumps(investigation.ai_analysis.model_dump()) if investigation.ai_analysis else None,
        json.dumps(investigation.decision.model_dump()),
        investigation.status, investigation.created_at, org_id
    ))
    conn.commit()
    conn.close()

def get_investigation_by_dispute_id(dispute_id: str, *, organization_id: str) -> Optional[Investigation]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM investigations WHERE dispute_id = ? AND organization_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (dispute_id, organization_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d['verification_results'] = json.loads(d['verification_results'])
        d['readiness_score'] = json.loads(d['readiness_score'])
        d['timeline'] = json.loads(d['timeline'])
        d['ai_analysis'] = json.loads(d['ai_analysis']) if d['ai_analysis'] else None
        d['decision'] = json.loads(d['decision'])
        return Investigation(**d)
    return None

def save_audit_event(event: AuditEvent):
    org_id = _require_org(event)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO audit_events
    (event_id, dispute_id, event_type, description, metadata, timestamp,
     organization_id, actor_user_id, resource_type, resource_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.event_id, event.dispute_id, event.event_type, event.description,
        json.dumps(event.metadata), event.timestamp,
        org_id, event.actor_user_id, event.resource_type, event.resource_id
    ))
    conn.commit()
    conn.close()

# Audit reads join users (same database) to show who acted. Users are only ever
# deactivated, never deleted, so actor attribution stays resolvable.
_AUDIT_SELECT = """
    SELECT a.*, u.name AS actor_name, u.email AS actor_email
    FROM audit_events a
    LEFT JOIN users u ON u.id = a.actor_user_id AND u.organization_id = a.organization_id
"""

def _audit_rows(rows) -> List[AuditEvent]:
    results = []
    for r in rows:
        d = dict(r)
        d['metadata'] = json.loads(d['metadata'])
        results.append(AuditEvent(**d))
    return results

def get_audit_events_by_dispute_id(dispute_id: str, *, organization_id: str) -> List[AuditEvent]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        _AUDIT_SELECT + " WHERE a.dispute_id = ? AND a.organization_id = ? ORDER BY a.timestamp ASC, a.rowid ASC",
        (dispute_id, organization_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return _audit_rows(rows)

def get_audit_events_for_organization(*, organization_id: str, limit: int = 50) -> List[AuditEvent]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        _AUDIT_SELECT + " WHERE a.organization_id = ? ORDER BY a.timestamp DESC, a.rowid DESC LIMIT ?",
        (organization_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return _audit_rows(rows)

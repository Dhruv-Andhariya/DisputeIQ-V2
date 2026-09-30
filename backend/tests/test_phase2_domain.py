"""Phase 2 merchant domain CRUD and tenant isolation."""
from conftest import auth_header, register_org


def _domain_chain(client, token):
    headers = auth_header(token)
    customer = client.post("/domain/customers", headers=headers, json={
        "external_customer_id": "CUS-1001",
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "phone": "+91-9000000000",
    })
    assert customer.status_code == 201, customer.text
    customer = customer.json()

    order = client.post("/domain/orders", headers=headers, json={
        "customer_id": customer["id"],
        "external_order_id": "ORDER-1001",
        "order_status": "PAID",
        "currency": "INR",
        "total_amount": 2499,
        "order_created_at": "2026-09-29T10:00:00Z",
    })
    assert order.status_code == 201, order.text
    order = order.json()

    transaction = client.post("/domain/transactions", headers=headers, json={
        "order_id": order["id"],
        "external_transaction_id": "TXN-1001",
        "payment_method": "card",
        "transaction_status": "SUCCESS",
        "amount": 2499,
        "currency": "INR",
        "transaction_type": "PAYMENT",
        "transaction_timestamp": "2026-09-29T10:01:00Z",
    })
    assert transaction.status_code == 201, transaction.text
    transaction = transaction.json()

    dispute = client.post("/domain/disputes", headers=headers, json={
        "customer_id": customer["id"],
        "order_id": order["id"],
        "transaction_id": transaction["id"],
        "external_dispute_id": "DSP-DOMAIN-1001",
        "dispute_type": "PAYMENT_DISPUTE",
        "reason": "Goods / Services Not Received",
        "description": "Customer reports the order was not received.",
        "opened_at": "2026-09-29T12:00:00Z",
    })
    assert dispute.status_code == 201, dispute.text
    return customer, order, transaction, dispute.json()


def test_phase2_domain_chain_bridges_to_existing_dispute_pipeline(client):
    merchant = register_org(client, "Domain Merchant", "admin@domain-merchant.com")
    customer, order, transaction, dispute = _domain_chain(client, merchant["access_token"])

    assert dispute["customer"]["id"] == customer["id"]
    assert dispute["order"]["id"] == order["id"]
    assert dispute["transaction"]["id"] == transaction["id"]
    assert dispute["legacy_dispute_id"].endswith("-DSP-DOMAIN-1001")

    legacy_disputes = client.get("/disputes", headers=auth_header(merchant["access_token"]))
    assert legacy_disputes.status_code == 200
    assert legacy_disputes.json()[0]["dispute_id"].endswith("-DSP-DOMAIN-1001")


def test_phase2_domain_resources_are_tenant_isolated(client):
    merchant_a = register_org(client, "Merchant A", "admin@merchant-a-domain.com")
    merchant_b = register_org(client, "Merchant B", "admin@merchant-b-domain.com")
    customer, order, transaction, dispute = _domain_chain(client, merchant_a["access_token"])
    headers_b = auth_header(merchant_b["access_token"])

    assert client.get(f"/domain/customers/{customer['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/domain/orders/{order['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/domain/transactions/{transaction['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/domain/disputes/{dispute['id']}", headers=headers_b).status_code == 404
    assert client.get("/domain/customers", headers=headers_b).json() == []
    assert client.get("/domain/orders", headers=headers_b).json() == []
    assert client.get("/domain/transactions", headers=headers_b).json() == []
    assert client.get("/domain/disputes", headers=headers_b).json() == []

"""Phase 4 document processing and extraction tests."""
from conftest import auth_header, register_org, seed_dispute_case
from app.document_intelligence.processors import extract_structured


def upload_json(client, token, dispute_id, filename="invoice.json", payload=None):
    payload = payload or {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-09-20",
        "customer_name": "Raj Patel",
        "order_id": "ORD-1001",
        "transaction_id": "TXN-1001",
        "total_amount": 79999,
        "currency": "INR",
    }
    import json
    return client.post(
        f"/domain/disputes/{dispute_id}/evidence",
        headers=auth_header(token),
        data={"evidence_type": "INVOICE", "source_type": "MERCHANT_UPLOAD"},
        files={"file": (filename, json.dumps(payload).encode(), "application/json")},
    )


def test_indian_currency_and_invoice_number_normalization_preserves_raw_ocr():
    raw_ocr = "Invoice No: INV-1001\nTotal Amount: ₹79,999\nSubtotal: Rs. 79,999.00\nTax: INR 79,999"

    structured, schema, _ = extract_structured("INVOICE", raw_ocr)

    assert schema == "invoice.v1"
    assert structured["invoice_number"] == "INV-1001"
    assert structured["total_amount"] == 79999.0
    assert structured["subtotal"] == 79999.0
    assert structured["tax"] == 79999.0
    assert raw_ocr == "Invoice No: INV-1001\nTotal Amount: ₹79,999\nSubtotal: Rs. 79,999.00\nTax: INR 79,999"


def test_json_document_processing_stores_raw_structured_and_provenance(client):
    merchant = register_org(client, "Processing Merchant", "admin@processing-merchant.com")
    dispute_id = seed_dispute_case(merchant["user"]["organization"]["id"], "PROCESSING")
    uploaded = upload_json(client, merchant["access_token"], dispute_id)
    assert uploaded.status_code == 201, uploaded.text
    evidence_id = uploaded.json()["id"]

    processed = client.post(f"/domain/evidence/{evidence_id}/process", headers=auth_header(merchant["access_token"]))
    assert processed.status_code == 200, processed.text
    result = processed.json()
    assert result["status"] == "PROCESSED"
    assert result["evidence_id"] == evidence_id
    assert result["processor"] == "BUILTIN_TEXT"
    assert result["processor_version"] == "1.0"
    assert result["document_type"] == "INVOICE"
    assert result["classification_confidence"] > 0.9
    assert result["extraction_schema"] == "invoice.v1"
    assert result["structured_data"]["invoice_number"] == "INV-1001"
    assert result["structured_data"]["total_amount"] == 79999.0
    assert result["structured_data"]["currency"] == "INR"
    assert result["raw_text"] and result["pages"][0]["page"] == 1
    assert result["confidence_metadata"]["ocr_confidence"] == 1.0
    assert result["confidence_metadata"]["vlm_used"] is False

    latest = client.get(f"/domain/evidence/{evidence_id}/processing", headers=auth_header(merchant["access_token"]))
    assert latest.status_code == 200
    assert latest.json()["id"] == result["id"]

    activity = client.get("/organizations/me/audit-events", headers=auth_header(merchant["access_token"])).json()
    event_types = {event["event_type"] for event in activity}
    assert {"DOCUMENT_PROCESSING_STARTED", "DOCUMENT_PROCESSED"} <= event_types


def test_processing_failure_can_be_retried_and_is_tenant_scoped(client):
    merchant_a = register_org(client, "Processing A", "admin@processing-a.com")
    merchant_b = register_org(client, "Processing B", "admin@processing-b.com")
    dispute_id = seed_dispute_case(merchant_a["user"]["organization"]["id"], "PROCESSING-A")
    uploaded = client.post(
        f"/domain/disputes/{dispute_id}/evidence",
        headers=auth_header(merchant_a["access_token"]),
        data={"evidence_type": "INVOICE", "source_type": "MERCHANT_UPLOAD"},
        files={"file": ("broken.pdf", b"%PDF-1.7 not a complete pdf", "application/pdf")},
    )
    evidence_id = uploaded.json()["id"]

    failed = client.post(f"/domain/evidence/{evidence_id}/process", headers=auth_header(merchant_a["access_token"]))
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert failed.json()["error_message"]

    retried = client.post(f"/domain/evidence/{evidence_id}/process", headers=auth_header(merchant_a["access_token"]))
    assert retried.status_code == 200
    assert retried.json()["status"] == "FAILED"
    assert retried.json()["attempt_count"] == 2

    headers_b = auth_header(merchant_b["access_token"])
    assert client.post(f"/domain/evidence/{evidence_id}/process", headers=headers_b).status_code == 404
    assert client.get(f"/domain/evidence/{evidence_id}/processing", headers=headers_b).status_code == 404

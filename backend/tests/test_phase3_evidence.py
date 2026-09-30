"""Phase 3 evidence ingestion, provenance, storage, and tenant isolation."""
import hashlib

from conftest import auth_header, register_org, seed_dispute_case


def upload(client, token, dispute_id, filename="receipt.pdf", content=b"%PDF-1.7 synthetic receipt"):
    return client.post(
        f"/domain/disputes/{dispute_id}/evidence",
        headers=auth_header(token),
        data={"evidence_type": "PAYMENT_RECEIPT", "source_type": "MERCHANT_UPLOAD"},
        files={"file": (filename, content, "application/pdf")},
    )


def test_upload_provenance_hash_download_duplicate_and_soft_delete(client, tmp_path, monkeypatch):
    merchant = register_org(client, "Evidence Merchant", "admin@evidence-merchant.com")
    dispute_id = seed_dispute_case(merchant["user"]["organization"]["id"], "EVIDENCE")
    content = b"%PDF-1.7 immutable synthetic receipt"

    first = upload(client, merchant["access_token"], dispute_id, content=content)
    assert first.status_code == 201, first.text
    first_record = first.json()
    assert first_record["organization_id"] == merchant["user"]["organization"]["id"]
    assert first_record["dispute_id"] == dispute_id
    assert first_record["evidence_type"] == "PAYMENT_RECEIPT"
    assert first_record["source_type"] == "MERCHANT_UPLOAD"
    assert first_record["uploaded_by_user_id"] == merchant["user"]["id"]
    assert first_record["content_hash"] == hashlib.sha256(content).hexdigest()
    assert first_record["status"] == "READY"

    duplicate = upload(client, merchant["access_token"], dispute_id, filename="copy.pdf", content=content)
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["metadata"]["duplicate_of"] == first_record["id"]

    listed = client.get(f"/domain/disputes/{dispute_id}/evidence", headers=auth_header(merchant["access_token"]))
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {first_record["id"], duplicate.json()["id"]}

    downloaded = client.get(f"/domain/evidence/{first_record['id']}/download", headers=auth_header(merchant["access_token"]))
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["content-type"].startswith("application/pdf")
    assert "receipt.pdf" in downloaded.headers["content-disposition"]

    activity = client.get("/organizations/me/audit-events", headers=auth_header(merchant["access_token"])).json()
    upload_events = [event for event in activity if event["event_type"] == "EVIDENCE_UPLOADED"]
    assert upload_events and upload_events[0]["actor_user_id"] == merchant["user"]["id"]

    deleted = client.delete(f"/domain/evidence/{first_record['id']}", headers=auth_header(merchant["access_token"]))
    assert deleted.status_code == 204
    assert client.get(f"/domain/evidence/{first_record['id']}", headers=auth_header(merchant["access_token"])).status_code == 404
    assert client.get(f"/domain/evidence/{first_record['id']}/download", headers=auth_header(merchant["access_token"])).status_code == 404


def test_evidence_validation_and_tenant_isolation(client):
    merchant_a = register_org(client, "Evidence A", "admin@evidence-a.com")
    merchant_b = register_org(client, "Evidence B", "admin@evidence-b.com")
    dispute_id = seed_dispute_case(merchant_a["user"]["organization"]["id"], "EVIDENCE-A")

    unsafe = upload(client, merchant_a["access_token"], dispute_id, filename="run.exe", content=b"MZ executable")
    assert unsafe.status_code == 400

    oversized = upload(client, merchant_a["access_token"], dispute_id, filename="large.pdf", content=b"x" * (10 * 1024 * 1024 + 1))
    assert oversized.status_code == 400

    created = upload(client, merchant_a["access_token"], dispute_id)
    evidence_id = created.json()["id"]
    headers_b = auth_header(merchant_b["access_token"])

    assert client.get(f"/domain/disputes/{dispute_id}/evidence", headers=headers_b).status_code == 404
    assert client.get(f"/domain/evidence/{evidence_id}", headers=headers_b).status_code == 404
    assert client.get(f"/domain/evidence/{evidence_id}/download", headers=headers_b).status_code == 404
    assert client.patch(f"/domain/evidence/{evidence_id}", headers=headers_b, json={"metadata": {"tampered": True}}).status_code == 404
    assert client.delete(f"/domain/evidence/{evidence_id}", headers=headers_b).status_code == 404
    assert upload(client, merchant_b["access_token"], dispute_id).status_code == 404

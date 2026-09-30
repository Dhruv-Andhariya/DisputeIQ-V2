"""
PERMANENT SECURITY REGRESSION TESTS: TENANT ISOLATION.

Merchant A must never read, modify, or even detect the existence of Merchant B's data.
Any new tenant-owned endpoint must be added to the matrices below.
"""
import sqlite3

import pytest

from app.database import db as legacy_db
from app.models.domain import Dispute
from conftest import TEST_DB_PATH, auth_header, create_member, login, register_org, seed_dispute_case


@pytest.fixture
def tenants(client):
    a = register_org(client, "Merchant A", "admin@merchant-a.com", name="Alice A")
    b = register_org(client, "Merchant B", "admin@merchant-b.com", name="Bob B")
    a_org, b_org = a["user"]["organization"]["id"], b["user"]["organization"]["id"]
    return {
        "a_token": a["access_token"], "a_org": a_org, "a_user": a["user"],
        "a_dispute": seed_dispute_case(a_org, "A001", case_index=0),
        "b_token": b["access_token"], "b_org": b_org, "b_user": b["user"],
        "b_dispute": seed_dispute_case(b_org, "B001", case_index=1),
    }


def _dispute_state(dispute_id):
    conn = sqlite3.connect(TEST_DB_PATH)
    row = conn.execute("SELECT status, updated_at, organization_id FROM disputes WHERE dispute_id = ?",
                       (dispute_id,)).fetchone()
    counts = tuple(
        conn.execute(f"SELECT COUNT(*) FROM {t} WHERE dispute_id = ?", (dispute_id,)).fetchone()[0]
        for t in ("audit_events", "investigations", "evidence")
    )
    conn.close()
    return row, counts


def _read_requests(dispute_id):
    return [
        ("GET", f"/disputes/{dispute_id}", None),
        ("GET", f"/disputes/{dispute_id}/evidence", None),
        ("GET", f"/disputes/{dispute_id}/timeline", None),
        ("GET", f"/disputes/{dispute_id}/audit", None),
        ("GET", f"/disputes/{dispute_id}/investigation", None),
    ]


def _write_requests(dispute_id):
    return [
        ("POST", f"/disputes/{dispute_id}/investigate", None),
        ("POST", f"/disputes/{dispute_id}/approve", {"notes": "cross-tenant"}),
        ("POST", f"/disputes/{dispute_id}/reject", {"notes": "cross-tenant"}),
        ("POST", "/demo/failure", {"dispute_id": dispute_id}),
    ]


def test_merchant_a_cannot_list_merchant_b_disputes(client, tenants):
    ids = [d["dispute_id"] for d in client.get("/disputes", headers=auth_header(tenants["a_token"])).json()]
    assert ids == [tenants["a_dispute"]]
    assert tenants["b_dispute"] not in ids


def test_merchant_a_cannot_read_any_merchant_b_dispute_resource(client, tenants):
    h = auth_header(tenants["a_token"])
    nonexistent = "DSP-NOPE01"
    for (method, url, body), (_, ghost_url, _) in zip(_read_requests(tenants["b_dispute"]), _read_requests(nonexistent)):
        res = client.request(method, url, headers=h, json=body)
        ghost = client.request(method, ghost_url, headers=h, json=body)
        # 404, not 403, and byte-for-byte the same as a dispute that doesn't exist:
        # A must not be able to learn that B's dispute exists.
        assert res.status_code == ghost.status_code == 404, (url, res.status_code, res.text)
        assert res.text == ghost.text.replace(nonexistent, tenants["b_dispute"])


def test_merchant_a_cannot_modify_merchant_b_dispute(client, tenants):
    before = _dispute_state(tenants["b_dispute"])
    h = auth_header(tenants["a_token"])  # A is ADMIN: holds every permission, but only within A

    for method, url, body in _write_requests(tenants["b_dispute"]):
        res = client.request(method, url, headers=h, json=body)
        assert res.status_code == 404, (url, res.status_code, res.text)

    # B's dispute is untouched: same status, no new audit events, investigations, or evidence
    assert _dispute_state(tenants["b_dispute"]) == before


def test_merchant_b_can_access_its_own_data(client, tenants):
    h = auth_header(tenants["b_token"])
    ids = [d["dispute_id"] for d in client.get("/disputes", headers=h).json()]
    assert ids == [tenants["b_dispute"]]

    for method, url, body in _write_requests(tenants["b_dispute"])[:1] + _read_requests(tenants["b_dispute"]):
        res = client.request(method, url, headers=h, json=body)
        assert res.status_code == 200, (url, res.status_code, res.text)

    evidence = client.get(f"/disputes/{tenants['b_dispute']}/evidence", headers=h).json()
    assert evidence and all(e["organization_id"] == tenants["b_org"] for e in evidence)

    trail = client.get(f"/disputes/{tenants['b_dispute']}/audit", headers=h).json()
    assert trail and all(e["organization_id"] == tenants["b_org"] for e in trail)
    assert all(e["actor_email"] == "admin@merchant-b.com" for e in trail if e["actor_user_id"])


def test_empty_organization_does_not_receive_global_evaluation_summary(client):
    body = register_org(client, "Empty Merchant", "admin@empty-merchant.com")
    res = client.get("/evaluation/summary", headers=auth_header(body["access_token"]))

    assert res.status_code == 200
    assert res.json() == {
        "status": "NOT_AVAILABLE",
        "message": "Benchmark evaluation is unavailable until this organization has disputes.",
    }


def test_client_supplied_organization_id_is_ignored(client, tenants):
    h = auth_header(tenants["a_token"])
    res = client.get(f"/disputes?organization_id={tenants['b_org']}", headers=h)
    assert [d["dispute_id"] for d in res.json()] == [tenants["a_dispute"]]

    # organization_id in a request body cannot place a user into another tenant
    res = client.post("/organizations/me/users", headers=h, json={
        "name": "Mole", "email": "mole@merchant-a.com", "password": "password123", "role": "ADMIN",
        "organization_id": tenants["b_org"],
    })
    assert res.status_code == 201
    mole_token = login(client, "mole@merchant-a.com", "password123")
    me = client.get("/auth/me", headers=auth_header(mole_token)).json()
    assert me["organization"]["id"] == tenants["a_org"]


def test_organization_endpoints_are_isolated(client, tenants):
    create_member(client, tenants["b_token"], "analyst@merchant-b.com", "ANALYST")
    a_h, b_h = auth_header(tenants["a_token"]), auth_header(tenants["b_token"])

    assert client.get("/organizations/me", headers=a_h).json()["id"] == tenants["a_org"]
    assert client.get("/organizations/me", headers=b_h).json()["id"] == tenants["b_org"]

    a_members = {m["email"] for m in client.get("/organizations/me/users", headers=a_h).json()}
    assert a_members == {"admin@merchant-a.com"}

    # A cannot modify (or detect) B's users
    b_members = client.get("/organizations/me/users", headers=b_h).json()
    b_analyst = next(m for m in b_members if m["email"] == "analyst@merchant-b.com")
    res = client.patch(f"/organizations/me/users/{b_analyst['id']}", headers=a_h,
                       json={"role": "ADMIN", "is_active": False})
    assert res.status_code == 404
    b_analyst_after = next(m for m in client.get("/organizations/me/users", headers=b_h).json()
                           if m["id"] == b_analyst["id"])
    assert b_analyst_after["role"] == "ANALYST" and b_analyst_after["is_active"] is True

    # A renaming its org does not touch B
    client.patch("/organizations/me", headers=a_h, json={"name": "Merchant A Renamed"})
    assert client.get("/organizations/me", headers=b_h).json()["name"] == "Merchant B"


def test_organization_audit_log_is_isolated(client, tenants):
    client.post(f"/disputes/{tenants['b_dispute']}/investigate", headers=auth_header(tenants["b_token"]))
    a_events = client.get("/organizations/me/audit-events", headers=auth_header(tenants["a_token"])).json()
    assert a_events
    assert all(e["organization_id"] == tenants["a_org"] for e in a_events)
    assert all(e["dispute_id"] != tenants["b_dispute"] for e in a_events)


def test_data_layer_refuses_unscoped_access():
    """Tenant filtering is not optional at the persistence layer."""
    with pytest.raises(TypeError):
        legacy_db.get_dispute_by_id("DSP-B001")  # organization_id is a required keyword
    with pytest.raises(TypeError):
        legacy_db.get_all_disputes()
    with pytest.raises(ValueError):
        legacy_db.save_dispute(Dispute(
            dispute_id="DSP-ORPHAN", payment_id="P", merchant_id="M", amount=1.0,
            dispute_date="2026-01-01", created_at="2026-01-01", updated_at="2026-01-01",
        ))

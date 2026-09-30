"""Registration, login, and token validation."""
import sqlite3
from datetime import timedelta

import jwt

from app.core.security import create_access_token
from conftest import DEFAULT_PASSWORD, TEST_DB_PATH, auth_header, create_member, login, register_org


def _db_row(sql, *params):
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ---------- Registration ----------

def test_register_creates_organization_admin_and_token(client):
    body = register_org(client, "ABC Electronics", "admin@abcelectronics.com")

    user = body["user"]
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["expires_in"] == 15 * 60
    assert user["role"] == "ADMIN"
    assert user["email"] == "admin@abcelectronics.com"
    assert user["organization"]["name"] == "ABC Electronics"
    assert user["organization"]["slug"] == "abc-electronics"
    assert "users:manage" in user["permissions"]

    org = _db_row("SELECT * FROM organizations WHERE id = ?", user["organization"]["id"])
    assert org is not None and org["is_active"] == 1
    db_user = _db_row("SELECT * FROM users WHERE id = ?", user["id"])
    assert db_user["organization_id"] == org["id"]

    # The returned token works immediately
    me = client.get("/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200 and me.json()["id"] == user["id"]


def test_password_is_hashed_never_stored_or_returned(client):
    body = register_org(client, "ABC Electronics", "admin@abcelectronics.com")
    stored = _db_row("SELECT password_hash FROM users WHERE id = ?", body["user"]["id"])["password_hash"]

    assert stored != DEFAULT_PASSWORD
    assert stored.startswith("$argon2id$")
    assert DEFAULT_PASSWORD not in str(body)
    assert stored not in str(body)
    assert not any("password" in key for key in [*body, *body["user"]])


def test_register_duplicate_email_conflicts_case_insensitively(client):
    register_org(client, "ABC Electronics", "admin@abcelectronics.com")
    res = client.post("/auth/register", json={
        "organization_name": "Other Co", "name": "X", "email": "ADMIN@ABCElectronics.com", "password": DEFAULT_PASSWORD,
    })
    assert res.status_code == 409
    # The failed registration must not leave an orphan organization behind
    assert _db_row("SELECT COUNT(*) AS n FROM organizations")["n"] == 1


def test_same_organization_name_gets_distinct_slugs(client):
    a = register_org(client, "ABC Electronics", "a@abc.com")
    b = register_org(client, "ABC Electronics", "b@abc.com")
    assert a["user"]["organization"]["slug"] != b["user"]["organization"]["slug"]
    assert a["user"]["organization"]["id"] != b["user"]["organization"]["id"]


def test_register_validates_input(client):
    base = {"organization_name": "ABC", "name": "Admin", "email": "admin@abc.com", "password": DEFAULT_PASSWORD}
    for override in ({"password": "short"}, {"email": "not-an-email"}, {"organization_name": " "}, {"name": ""}):
        res = client.post("/auth/register", json={**base, **override})
        assert res.status_code == 422, override


# ---------- Login ----------

def test_login_with_valid_credentials(client):
    register_org(client, "ABC Electronics", "admin@abcelectronics.com")
    res = client.post("/auth/login", json={"email": "Admin@ABCelectronics.com", "password": DEFAULT_PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["last_login_at"] is not None


def test_login_wrong_password_and_unknown_email_fail_identically(client):
    register_org(client, "ABC Electronics", "admin@abcelectronics.com")
    wrong_pw = client.post("/auth/login", json={"email": "admin@abcelectronics.com", "password": "wrong-password"})
    unknown = client.post("/auth/login", json={"email": "nobody@abcelectronics.com", "password": DEFAULT_PASSWORD})

    assert wrong_pw.status_code == unknown.status_code == 401
    # Same message: responses must not reveal which emails are registered
    assert wrong_pw.json() == unknown.json() == {"detail": "Invalid email or password."}


def test_login_of_deactivated_user_is_refused(client):
    admin = register_org(client, "ABC Electronics", "admin@abc.com")
    member = create_member(client, admin["access_token"], "viewer@abc.com", "VIEWER")
    client.patch(f"/organizations/me/users/{member['id']}", headers=auth_header(admin["access_token"]),
                 json={"is_active": False})

    res = client.post("/auth/login", json={"email": "viewer@abc.com", "password": DEFAULT_PASSWORD})
    assert res.status_code == 403


# ---------- Token validation ----------

def test_protected_endpoint_without_token_is_401(client):
    res = client.get("/auth/me")
    assert res.status_code == 401
    assert res.headers.get("www-authenticate") == "Bearer"
    assert client.get("/disputes").status_code == 401


def test_malformed_and_forged_tokens_are_rejected(client):
    body = register_org(client, "ABC Electronics", "admin@abc.com")
    forged = jwt.encode({"sub": body["user"]["id"], "type": "access", "iat": 0, "exp": 9999999999},
                        "attacker-secret-attacker-secret-attacker-secret", algorithm="HS256")
    unsigned = jwt.encode({"sub": body["user"]["id"], "type": "access", "iat": 0, "exp": 9999999999},
                          None, algorithm="none")

    for token in ("garbage", forged, unsigned, body["access_token"] + "x"):
        assert client.get("/auth/me", headers=auth_header(token)).status_code == 401, token
    assert client.get("/auth/me", headers={"Authorization": body["access_token"]}).status_code == 401


def test_expired_token_is_rejected(client):
    body = register_org(client, "ABC Electronics", "admin@abc.com")
    expired, _ = create_access_token(body["user"]["id"], expires_delta=timedelta(seconds=-1))
    res = client.get("/auth/me", headers=auth_header(expired))
    assert res.status_code == 401
    assert res.json() == {"detail": "Invalid or expired token."}


def test_token_of_deactivated_user_stops_working_immediately(client):
    admin = register_org(client, "ABC Electronics", "admin@abc.com")
    create_member(client, admin["access_token"], "inv@abc.com", "INVESTIGATOR")
    inv_token = login(client, "inv@abc.com")
    assert client.get("/auth/me", headers=auth_header(inv_token)).status_code == 200

    members = client.get("/organizations/me/users", headers=auth_header(admin["access_token"])).json()
    inv_id = next(m["id"] for m in members if m["email"] == "inv@abc.com")
    client.patch(f"/organizations/me/users/{inv_id}", headers=auth_header(admin["access_token"]),
                 json={"is_active": False})

    assert client.get("/auth/me", headers=auth_header(inv_token)).status_code == 401


def test_me_returns_user_and_organization(client):
    body = register_org(client, "ABC Electronics", "admin@abc.com", name="Admin User")
    me = client.get("/auth/me", headers=auth_header(body["access_token"])).json()
    assert me["name"] == "Admin User"
    assert me["role"] == "ADMIN"
    assert me["organization"] == {"id": body["user"]["organization"]["id"], "name": "ABC Electronics",
                                  "slug": "abc-electronics"}
    assert "password_hash" not in me


def test_login_and_logout_are_audited_with_actor(client):
    body = register_org(client, "ABC Electronics", "admin@abc.com")
    token = login(client, "admin@abc.com")
    assert client.post("/auth/logout", headers=auth_header(token)).status_code == 204

    events = client.get("/organizations/me/audit-events", headers=auth_header(token)).json()
    types = [e["event_type"] for e in events]
    assert {"ORGANIZATION_REGISTERED", "USER_LOGIN", "USER_LOGOUT"} <= set(types)
    for e in events:
        assert e["actor_user_id"] == body["user"]["id"]
        assert e["actor_email"] == "admin@abc.com"
        assert e["organization_id"] == body["user"]["organization"]["id"]

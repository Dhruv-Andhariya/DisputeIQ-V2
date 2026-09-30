"""Role-based authorization: who may do what inside their own organization."""
import pytest

from app.auth.permissions import ROLE_PERMISSIONS, Permission
from app.users.models import Role
from conftest import auth_header, create_member, login, register_org, seed_dispute_case


@pytest.fixture
def org(client):
    """One organization with a user of every role and one dispute case."""
    admin = register_org(client, "ABC Electronics", "admin@abc.com")
    tokens = {"ADMIN": admin["access_token"]}
    for role in ("INVESTIGATOR", "ANALYST", "VIEWER"):
        create_member(client, admin["access_token"], f"{role.lower()}@abc.com", role)
        tokens[role] = login(client, f"{role.lower()}@abc.com")
    dispute_id = seed_dispute_case(admin["user"]["organization"]["id"], "RBAC")
    return {"tokens": tokens, "dispute_id": dispute_id, "org_id": admin["user"]["organization"]["id"]}


def test_every_role_can_log_in_and_sees_its_permissions(client, org):
    for role, token in org["tokens"].items():
        me = client.get("/auth/me", headers=auth_header(token)).json()
        assert me["role"] == role
        assert set(me["permissions"]) == {p.value for p in ROLE_PERMISSIONS[Role(role)]}


def test_all_roles_can_read_cases(client, org):
    for role, token in org["tokens"].items():
        h = auth_header(token)
        assert client.get("/disputes", headers=h).status_code == 200, role
        assert client.get(f"/disputes/{org['dispute_id']}", headers=h).status_code == 200, role
        assert client.get(f"/disputes/{org['dispute_id']}/evidence", headers=h).status_code == 200, role
        assert client.get(f"/disputes/{org['dispute_id']}/audit", headers=h).status_code == 200, role


@pytest.mark.parametrize("role,allowed", [("ADMIN", True), ("INVESTIGATOR", True), ("ANALYST", False), ("VIEWER", False)])
def test_only_investigators_and_admins_can_investigate(client, org, role, allowed):
    res = client.post(f"/disputes/{org['dispute_id']}/investigate", headers=auth_header(org["tokens"][role]))
    assert res.status_code == (200 if allowed else 403)
    res = client.post("/demo/failure", headers=auth_header(org["tokens"][role]), json={"dispute_id": org["dispute_id"]})
    assert res.status_code == (200 if allowed else 403)


@pytest.mark.parametrize("role,allowed", [("ADMIN", True), ("INVESTIGATOR", False), ("ANALYST", False), ("VIEWER", False)])
def test_only_admins_can_make_final_review_decision(client, org, role, allowed):
    res = client.post(f"/disputes/{org['dispute_id']}/approve", headers=auth_header(org["tokens"][role]), json={})
    assert res.status_code == (200 if allowed else 403)


def test_read_only_roles_cannot_trigger_pipeline_via_timeline(client, org):
    h = auth_header(org["tokens"]["VIEWER"])
    assert client.get(f"/disputes/{org['dispute_id']}/timeline", headers=h).status_code == 404
    assert client.get(f"/disputes/{org['dispute_id']}/investigation", headers=h).status_code == 404

    client.post(f"/disputes/{org['dispute_id']}/investigate", headers=auth_header(org["tokens"]["INVESTIGATOR"]))
    assert client.get(f"/disputes/{org['dispute_id']}/timeline", headers=h).status_code == 200
    assert client.get(f"/disputes/{org['dispute_id']}/investigation", headers=h).status_code == 200


@pytest.mark.parametrize("role", ["INVESTIGATOR", "ANALYST", "VIEWER"])
def test_non_admins_cannot_manage_users_or_organization(client, org, role):
    h = auth_header(org["tokens"][role])
    assert client.get("/organizations/me/users", headers=h).status_code == 403
    assert client.post("/organizations/me/users", headers=h, json={
        "name": "Sneaky", "email": f"sneaky-{role}@abc.com", "password": "password123", "role": "ADMIN",
    }).status_code == 403
    assert client.patch("/organizations/me", headers=h, json={"name": "Hijacked"}).status_code == 403
    assert client.get("/organizations/me/audit-events", headers=h).status_code == 403
    # Every member may read their own organization's basic details
    assert client.get("/organizations/me", headers=h).status_code == 200


def test_admin_manages_users_and_organization(client, org):
    h = auth_header(org["tokens"]["ADMIN"])
    members = client.get("/organizations/me/users", headers=h).json()
    assert {m["role"] for m in members} == {"ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"}
    assert all("password_hash" not in m for m in members)

    viewer = next(m for m in members if m["role"] == "VIEWER")
    res = client.patch(f"/organizations/me/users/{viewer['id']}", headers=h, json={"role": "ANALYST"})
    assert res.status_code == 200 and res.json()["role"] == "ANALYST"

    res = client.patch("/organizations/me", headers=h, json={"name": "ABC Electronics Ltd"})
    assert res.status_code == 200 and res.json()["name"] == "ABC Electronics Ltd"

    assert client.post("/organizations/me/users", headers=h, json={
        "name": "Dup", "email": "viewer@abc.com", "password": "password123", "role": "VIEWER",
    }).status_code == 409


def test_admin_cannot_demote_or_deactivate_self(client, org):
    h = auth_header(org["tokens"]["ADMIN"])
    me = client.get("/auth/me", headers=h).json()
    assert client.patch(f"/organizations/me/users/{me['id']}", headers=h, json={"role": "VIEWER"}).status_code == 400
    assert client.patch(f"/organizations/me/users/{me['id']}", headers=h, json={"is_active": False}).status_code == 400


def test_role_change_takes_effect_without_new_token(client, org):
    admin_h = auth_header(org["tokens"]["ADMIN"])
    viewer_h = auth_header(org["tokens"]["VIEWER"])
    assert client.post(f"/disputes/{org['dispute_id']}/investigate", headers=viewer_h).status_code == 403

    viewer = next(m for m in client.get("/organizations/me/users", headers=admin_h).json() if m["role"] == "VIEWER")
    client.patch(f"/organizations/me/users/{viewer['id']}", headers=admin_h, json={"role": "INVESTIGATOR"})

    assert client.post(f"/disputes/{org['dispute_id']}/investigate", headers=viewer_h).status_code == 200


def test_human_decisions_are_attributed_to_the_real_user(client, org):
    admin_h = auth_header(org["tokens"]["ADMIN"])
    inv_h = auth_header(org["tokens"]["INVESTIGATOR"])
    client.post(f"/disputes/{org['dispute_id']}/investigate", headers=inv_h)
    client.post(f"/disputes/{org['dispute_id']}/approve", headers=admin_h, json={"notes": "POD verified"})

    trail = client.get(f"/disputes/{org['dispute_id']}/audit", headers=admin_h).json()
    by_type = {e["event_type"]: e for e in trail}
    assert by_type["EVIDENCE_RETRIEVED"]["actor_email"] == "investigator@abc.com"
    assert by_type["HUMAN_APPROVED"]["actor_email"] == "admin@abc.com"
    assert by_type["HUMAN_APPROVED"]["metadata"]["notes"] == "POD verified"
    assert all(e["organization_id"] == org["org_id"] for e in trail)


def test_permission_matrix_is_as_specified():
    """Guards against accidental privilege changes in ROLE_PERMISSIONS."""
    assert ROLE_PERMISSIONS[Role.ADMIN] == frozenset(Permission)
    assert ROLE_PERMISSIONS[Role.INVESTIGATOR] == {Permission.VIEW_CASES, Permission.INVESTIGATE}
    assert ROLE_PERMISSIONS[Role.ANALYST] == {Permission.VIEW_CASES}
    assert ROLE_PERMISSIONS[Role.VIEWER] == {Permission.VIEW_CASES}

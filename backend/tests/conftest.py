"""
Shared test fixtures.

Tests run against a throwaway SQLite file built by the real Alembic migration chain,
never against the development database. Environment is fixed *before* any app import.
"""
import json
import os
import sqlite3
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="disputeiq-tests-")
TEST_DB_PATH = Path(_TMP_DIR) / "test.db"

os.environ.update({
    "ENV": "test",
    "DATABASE_URL": f"sqlite:///{TEST_DB_PATH.as_posix()}",
    "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256-signing",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "GEMINI_API_KEY": "",  # forces the deterministic AI fallback; tests never call Gemini
    "AUTO_MIGRATE": "false",
    "SEED_DEMO_DATA": "false",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import BASE_DIR  # noqa: E402
from app.core.migrations import upgrade_to_head  # noqa: E402
from app.database import db as legacy_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.domain import Delivery, Dispute, Evidence, Order, Payment  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    upgrade_to_head()
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Every test starts from an empty (but fully migrated) database."""
    yield
    conn = sqlite3.connect(TEST_DB_PATH)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('alembic_version') "
        "AND name NOT LIKE 'sqlite_%'"
    )]
    conn.execute("PRAGMA foreign_keys=OFF")
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    return TestClient(app)


# ---------- helpers ----------

DEFAULT_PASSWORD = "correct-horse-battery"


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_org(client, org_name: str, email: str, name: str = "Admin User", password: str = DEFAULT_PASSWORD) -> dict:
    res = client.post("/auth/register", json={
        "organization_name": org_name, "name": name, "email": email, "password": password,
    })
    assert res.status_code == 201, res.text
    return res.json()


def login(client, email: str, password: str = DEFAULT_PASSWORD) -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def create_member(client, admin_token: str, email: str, role: str, password: str = DEFAULT_PASSWORD) -> dict:
    res = client.post("/organizations/me/users", headers=auth_header(admin_token), json={
        "name": f"{role.title()} User", "email": email, "password": password, "role": role,
    })
    assert res.status_code == 201, res.text
    return res.json()


def seed_dispute_case(organization_id: str, tag: str, case_index: int = 0) -> str:
    """
    Stores one complete synthetic dispute case (dispute, payment, order, delivery, evidence)
    owned by `organization_id`, with ids rewritten to be unique. Returns the dispute id.
    """
    dataset = json.loads((BASE_DIR / "data" / "synthetic" / "dataset.json").read_text())
    case = dataset[case_index]
    d = case["dispute"]
    raw = json.dumps(case)
    for old, new in [
        (d["dispute_id"], f"DSP-{tag}"),
        (d["payment_id"], f"PAY-{tag}"),
        (case["order"]["order_id"], f"ORD-{tag}"),
        (case["delivery"]["delivery_id"], f"DEL-{tag}"),
        (f"EVD-{d['dispute_id'].split('-')[-1]}-", f"EVD-{tag}-"),
    ]:
        raw = raw.replace(f'"{old}', f'"{new}')
    case = json.loads(raw)

    org = {"organization_id": organization_id}
    legacy_db.save_dispute(Dispute(**case["dispute"], **org))
    legacy_db.save_payment(Payment(**case["payment"], **org))
    legacy_db.save_order(Order(**case["order"], **org))
    legacy_db.save_delivery(Delivery(**case["delivery"], **org))
    for ev in case["evidence"]:
        legacy_db.save_evidence(Evidence(**ev, **org))
    return case["dispute"]["dispute_id"]

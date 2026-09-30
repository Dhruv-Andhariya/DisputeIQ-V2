"""Migrations build a fresh schema and adopt pre-Phase-1 databases without data loss."""
import sqlite3

from app.core.migrations import downgrade_to, upgrade_to, upgrade_to_head


def _conn(path):
    return sqlite3.connect(path)


def test_fresh_database_migrates_to_head(tmp_path):
    path = tmp_path / "fresh.db"
    upgrade_to_head(f"sqlite:///{path.as_posix()}")

    conn = _conn(path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"organizations", "users", "disputes", "evidence", "audit_events"} <= tables
    audit_cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_events)")}
    assert {"organization_id", "actor_user_id", "resource_type", "resource_id"} <= audit_cols
    # Fresh DB has no legacy data, so no demo organization is created by the migration
    assert conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0
    conn.close()


def test_legacy_data_is_backfilled_into_demo_organization_and_survives_roundtrip(tmp_path):
    path = tmp_path / "legacy.db"
    url = f"sqlite:///{path.as_posix()}"
    upgrade_to("0001", url)  # the pre-Phase-1 schema

    conn = _conn(path)
    conn.execute("INSERT INTO disputes VALUES ('DSP-1','PAY-1','M',10.0,'INR','r','OPEN','d','STRONG_CASE','c','u')")
    conn.execute("INSERT INTO audit_events VALUES ('AUD-1','DSP-1','DISPUTE_RECEIVED','desc','{}','t')")
    conn.commit()
    conn.close()

    upgrade_to_head(url)
    conn = _conn(path)
    org_id, slug = conn.execute("SELECT id, slug FROM organizations").fetchone()
    assert slug == "demo-merchant"
    assert conn.execute("SELECT organization_id FROM disputes WHERE dispute_id='DSP-1'").fetchone()[0] == org_id
    assert conn.execute(
        "SELECT organization_id, resource_type, resource_id FROM audit_events WHERE event_id='AUD-1'"
    ).fetchone() == (org_id, "DISPUTE", "DSP-1")
    conn.close()

    downgrade_to("0001", url)
    upgrade_to_head(url)
    conn = _conn(path)
    assert conn.execute("SELECT COUNT(*) FROM disputes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM disputes WHERE organization_id IS NULL").fetchone()[0] == 0
    conn.close()

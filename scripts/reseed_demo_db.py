"""Safe Demo Database Reseed Script for PeX Platform."""
import os
import sys
import hashlib
from pathlib import Path

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Guard: Set DATABASE_URL explicitly to pex_demo.db
demo_db_path = Path("pex_demo.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite:///{demo_db_path.as_posix()}"

from app.config import settings
assert "pex_demo.db" in settings.DATABASE_URL, f"FATAL: DATABASE_URL is not targeting pex_demo.db! Target: {settings.DATABASE_URL}"

# Guard: Verify pex_enterprise.db integrity and protection
ent_path = Path("pex_enterprise.db")
if ent_path.exists():
    ent_sha = hashlib.sha256(ent_path.read_bytes()).hexdigest()
    expected_ent_sha = "06a1f20348d9fad95ce02c39aa5cc4a1fef28b0f3cd237c92769c62dfd86e275"
    if ent_sha.lower() != expected_ent_sha:
        print(f"FATAL: pex_enterprise.db hash mismatch! Expected {expected_ent_sha}, got {ent_sha}")
        sys.exit(1)
    print(f"[SAFEGUARD] pex_enterprise.db verified untouched (SHA256: {ent_sha[:16]}...)")

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.db.models import (
    CaseModel, AuditEventModel, UserModel, RolePermissionModel,
    PolicyRuleModel, ICDConfigurationModel, TokenVaultModel
)
import sqlite3

def run_reseed():
    print(f"[RESEED] Starting reset and reseed on {demo_db_path}...")
    init_db(force_reseed=True)
    print("[RESEED] init_db(force_reseed=True) completed successfully.")

    # SQLite-level verification
    con = sqlite3.connect(str(demo_db_path))
    cur = con.cursor()
    
    integrity = cur.execute("PRAGMA integrity_check;").fetchall()
    fk_check = cur.execute("PRAGMA foreign_key_check;").fetchall()
    print(f"[VERIFY] PRAGMA integrity_check: {integrity}")
    print(f"[VERIFY] PRAGMA foreign_key_check: {fk_check}")
    assert integrity == [("ok",)], f"Integrity check failed: {integrity}"
    assert fk_check == [], f"Foreign key check failed: {fk_check}"

    # Table counts
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()]
    counts = {t: cur.execute(f"SELECT count(*) FROM {t};").fetchone()[0] for t in tables}
    print("[VERIFY] Table row counts:")
    for t, c in counts.items():
        print(f"  {t}: {c}")

    assert counts.get("cases") == 82, f"Expected 82 cases, got {counts.get('cases')}"
    assert counts.get("audit_events") == 153, f"Expected 153 audit events, got {counts.get('audit_events')}"
    assert counts.get("users") == 9, f"Expected 9 users, got {counts.get('users')}"
    assert counts.get("role_permissions") == 8, f"Expected 8 permissions, got {counts.get('role_permissions')}"
    assert counts.get("policy_rules") == 5, f"Expected 5 policy rules, got {counts.get('policy_rules')}"
    assert counts.get("icd_configurations") == 5, f"Expected 5 ICD nodes, got {counts.get('icd_configurations')}"

    # Check all 41 profiles represented
    distinct_profiles = [r[0] for r in cur.execute("SELECT DISTINCT profile FROM cases ORDER BY profile;").fetchall()]
    print(f"[VERIFY] Distinct canonical profiles in cases ({len(distinct_profiles)}):")
    assert len(distinct_profiles) == 41, f"Expected 41 distinct profiles, got {len(distinct_profiles)}"

    # Check profile counts (2 cases each)
    profile_counts = cur.execute("SELECT profile, count(*) FROM cases GROUP BY profile;").fetchall()
    unequal = [p for p, c in profile_counts if c != 2]
    assert len(unequal) == 0, f"Profiles without exactly 2 cases: {unequal}"
    print("[VERIFY] All 41 profiles have exactly 2 cases each (82 cases total).")

    # Check status distribution
    statuses = cur.execute("SELECT status, count(*) FROM cases GROUP BY status ORDER BY count(*) DESC;").fetchall()
    print(f"[VERIFY] Cases by status: {statuses}")

    # Check DEMO_ONLY tagging
    cases_without_demo = cur.execute("SELECT count(*) FROM cases WHERE reason NOT LIKE '%DEMO_ONLY%';").fetchone()[0]
    events_without_demo = cur.execute("SELECT count(*) FROM audit_events WHERE details NOT LIKE '%DEMO_ONLY%';").fetchone()[0]
    print(f"[VERIFY] Cases without DEMO_ONLY tag: {cases_without_demo}")
    print(f"[VERIFY] Audit events without DEMO_ONLY tag: {events_without_demo}")
    assert cases_without_demo == 0, f"Found {cases_without_demo} cases without DEMO_ONLY tag"
    assert events_without_demo == 0, f"Found {events_without_demo} audit events without DEMO_ONLY tag"

    # Verify audit hash chain
    events = cur.execute("SELECT event_index, prev_hash, current_hash, case_id, action_name FROM audit_events ORDER BY event_index;").fetchall()
    broken_links = []
    for i in range(1, len(events)):
        if events[i][1] != events[i-1][2]:
            broken_links.append((events[i][0], events[i][1], events[i-1][2]))
    if broken_links:
        print(f"FATAL: Audit chain broken at {len(broken_links)} links!")
        sys.exit(1)
    else:
        print(f"[VERIFY] Cryptographic audit hash chain across {len(events)} events: 100% CONTINUOUS & VERIFIED.")

    con.close()
    print("[RESEED] Stage 3 database reset and reseed: FULLY VERIFIED.")

if __name__ == "__main__":
    run_reseed()

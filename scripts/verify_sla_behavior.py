"""SLA Verification Script for Reseeded Demo Dataset."""
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.schemas.canonical import LifecycleStage

def verify_sla():
    db_path = Path("pex_demo.db")
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM cases;").fetchall()
    total_cases = len(rows)
    print(f"Total cases in DB: {total_cases}")

    # Check for stale cases (from yesterday 2026-10-15 or manual test)
    stale_cases = [r for r in rows if not r["created_at"].startswith("2026-10-16")]
    manual_cases = [r for r in rows if r["case_id"] == "DQ-01_manual_test_iban_repair" or r["profile"] == "DQ-01"]
    print(f"Stale cases not from 2026-10-16: {len(stale_cases)}")
    print(f"Pre-reset manual test cases: {len(manual_cases)}")
    assert len(stale_cases) == 0, f"Found {len(stale_cases)} stale cases!"
    assert len(manual_cases) == 0, f"Found manual test cases in clean demo DB!"

    open_cases = [r for r in rows if r["status"] not in [LifecycleStage.SETTLED.value, LifecycleStage.REJECTED.value]]
    resolved_cases = [r for r in rows if r["status"] in [LifecycleStage.SETTLED.value, LifecycleStage.REJECTED.value]]
    print(f"Open cases count: {len(open_cases)}")
    print(f"Resolved cases count: {len(resolved_cases)}")
    assert len(open_cases) + len(resolved_cases) == total_cases

    # Run analytics SLA calculation
    now = datetime.utcnow()
    print(f"Current UTC time for SLA calculation: {now.isoformat()}")

    critical_1h = 0
    urgent_4h = 0
    safe_4h = 0
    overdue = 0

    overdue_details = []

    for r in open_cases:
        due_str = r["sla_due_at"]
        due_dt = datetime.fromisoformat(due_str.replace("Z", "+00:00").split("+")[0])
        created_dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00").split("+")[0])
        diff_sec = (due_dt - now).total_seconds()
        elapsed_sec = (now - created_dt).total_seconds()

        if diff_sec < 0:
            overdue += 1
            overdue_details.append({
                "case_id": r["case_id"],
                "profile": r["profile"],
                "status": r["status"],
                "queue": r["queue"],
                "created_at": r["created_at"],
                "sla_due_at": r["sla_due_at"],
                "elapsed_minutes": round(elapsed_sec / 60.0, 1),
                "overdue_by_minutes": round(abs(diff_sec) / 60.0, 1)
            })
        elif diff_sec <= 3600:
            critical_1h += 1
        elif diff_sec <= 14400:
            urgent_4h += 1
        else:
            safe_4h += 1

    print("\n--- SLA Breakdown (Open Cases) ---")
    print(f"  Overdue (breached): {overdue}")
    print(f"  Critical (< 1 hour remaining): {critical_1h}")
    print(f"  Urgent (1 to 4 hours remaining): {urgent_4h}")
    print(f"  Safe (> 4 hours remaining): {safe_4h}")
    print(f"  Settled / Resolved (excluded from SLA queue): {len(resolved_cases)}")

    # Check resolved cases SLA - confirm none are counted as overdue work
    for r in resolved_cases:
        assert r["status"] == LifecycleStage.SETTLED.value
        due_dt = datetime.fromisoformat(r["sla_due_at"].replace("Z", "+00:00").split("+")[0])
        settled_dt = datetime.fromisoformat(r["settled_at"].replace("Z", "+00:00").split("+")[0])
        assert settled_dt <= due_dt + datetime.resolution, "Settled after SLA unexpectedly"

    print("\n[VERIFIED] Resolved cases are strictly excluded from open overdue queue.")
    print(f"\nOverdue cases sample ({len(overdue_details)} total):")
    for od in overdue_details[:5]:
        print(f"  {od['case_id']} | {od['profile']} | {od['status']} | Created: {od['created_at']} | Elapsed: {od['elapsed_minutes']}m | Overdue by: {od['overdue_by_minutes']}m")

    con.close()

if __name__ == "__main__":
    verify_sla()

import sqlite3
import hashlib
from pathlib import Path

def main():
    db_path = Path("pex_demo.db")
    if not db_path.exists():
        print("pex_demo.db not found!")
        return

    sha256 = hashlib.sha256(db_path.read_bytes()).hexdigest()
    size = db_path.stat().st_size
    print(f"pex_demo.db size: {size} bytes")
    print(f"pex_demo.db sha256: {sha256}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print("Tables:", tables)
    counts = {}
    for t in tables:
        counts[t] = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print("Row counts:")
    for t, cnt in counts.items():
        print(f"  {t}: {cnt}")
    
    print("PRAGMA integrity_check:", cur.execute("PRAGMA integrity_check").fetchall())
    print("PRAGMA foreign_key_check:", cur.execute("PRAGMA foreign_key_check").fetchall())

    # Check profiles in cases table
    if "cases" in tables:
        profiles = [r[0] for r in cur.execute("SELECT DISTINCT profile FROM cases ORDER BY profile").fetchall()]
        print(f"Distinct profiles in cases ({len(profiles)}):", profiles)
        statuses = cur.execute("SELECT status, count(*) FROM cases GROUP BY status").fetchall()
        print("Cases by status:", statuses)

    # Check audit chain
    if "audit_events" in tables:
        events = cur.execute("SELECT event_index, prev_hash, current_hash, case_id, action_name FROM audit_events ORDER BY event_index").fetchall()
        print(f"Total audit events: {len(events)}")
        # verify hash chain
        broken = []
        for i in range(1, len(events)):
            if events[i][1] != events[i-1][2]:
                broken.append((events[i][0], events[i][1], events[i-1][2]))
        if broken:
            print(f"Audit chain BROKEN at {len(broken)} links:", broken[:5])
        else:
            print("Audit chain cryptographic links: VERIFIED OK")

    con.close()

if __name__ == "__main__":
    main()

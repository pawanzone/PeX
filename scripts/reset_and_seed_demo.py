#!/usr/bin/env python3
"""Reset the PeX demo database and seed everything a demo or a manual test round needs.

Steps: (1) delete the SQLite database files, (2) create the tables and the baseline cases and personas, (3) seed the showcase
cases and the STP batch, (4) seed the manual-test pack (one case for each of the 41 profiles plus the full-workflow sets).

Stop the backend first, run this, then start the backend. Usage:
    python scripts/reset_and_seed_demo.py [--db sqlite:///pex_v2.db] [--no-testpack] [--list]
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("DATABASE_URL", "sqlite:///pex_v2.db"), help="database URL (default: the demo database)")
    ap.add_argument("--no-testpack", action="store_true", help="skip the manual-test pack")
    ap.add_argument("--list", action="store_true", help="print every test-pack case id")
    a = ap.parse_args()
    os.environ["DATABASE_URL"] = a.db
    os.environ.setdefault("PEX_DEMO", "true")
    os.environ.setdefault("PEX_OPERATION_MODE", "ASSISTED")
    os.chdir(ROOT / "backend")

    # 1. wipe: only SQLite files under the backend folder are touched
    if a.db.startswith("sqlite:///"):
        p = Path(a.db.replace("sqlite:///", "", 1))
        p = p if p.is_absolute() else (ROOT / "backend" / p)
        for suffix in ("", "-shm", "-wal", "-journal"):
            f = Path(str(p) + suffix)
            if f.exists():
                f.unlink()
                print("removed", f.name)

    # 2-3. tables, baseline, showcase (init_db auto-seeds the showcase on an empty database)
    from app.db.init_db import create_tables, init_db
    from app.db.session import SessionLocal
    from app.db.models import CaseModel
    from app.services.v2 import seed
    create_tables()
    init_db()
    db = SessionLocal()
    try:
        if not db.query(CaseModel).filter(CaseModel.case_id == seed.MARKER).first():
            print("showcase:", seed.seed_v2(db))
        else:
            print("showcase: seeded on init")
    finally:
        db.close()

    # 4. manual-test pack
    if not a.no_testpack:
        from app.services.v2 import testpack
        r = testpack.seed_testpack()
        print(f"test pack: {r['cases']} cases")
        if a.list:
            for cid in r["ids"]:
                print("  ", cid)
    print("Done. Start the backend now.")


if __name__ == "__main__":
    main()

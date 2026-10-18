#!/usr/bin/env python3
"""Seed the UI v2 showcase cases (idempotent).
Usage: python scripts/seed_ui_v2_demo.py [--force] [--demo-batch]
  --demo-batch  also push a ~50 record synthetic batch (with duplicates, rejects and a possible duplicate) through the real pipeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def main():
    from app.db.init_db import create_tables, init_db
    from app.db.session import SessionLocal
    from app.db.models import CaseModel
    from app.services.v2 import seed
    create_tables()
    init_db()  # baseline 82 cases + personas (auto-seeds v2 on a fresh DB)
    db = SessionLocal()
    try:
        force = "--force" in sys.argv
        if force or not db.query(CaseModel).filter(CaseModel.case_id == seed.MARKER).first():
            print(seed.seed_v2(db))
        else:
            print("UI v2 demo data already present (use --force to re-create).")
        if "--demo-batch" in sys.argv:
            demo_batch()
    finally:
        db.close()


def demo_batch():
    import json
    import random
    import tempfile
    from app.services.batch_pipeline import get_pipeline
    from app.services.synthetic_batch import generate_records
    seed = random.randint(10**6, 10**9)
    recs = list(generate_records(44, seed=seed))
    dup = json.loads(json.dumps(recs[0]))  # same reference/amount/creditor, new ids -> "Needs review"
    dup["exception_id"] += "-B"
    dup["payment_info"]["payment_id"] += "-B"
    dup["payment_info"]["uetr"] = "9d1c2a40-0b1e-4c1c-8f00-" + f"{seed:012d}"[:12]
    bad = [dict(recs[1], exception_id=recs[1]["exception_id"] + "-X", profile_id="ZZ-99") for _ in range(2)]
    exact = [recs[2], recs[3]]  # exact duplicates inside the file
    lines = recs + [dup] + bad + exact
    with tempfile.TemporaryDirectory() as d:
        f = f"{d}/DEMO-ADAPTER-{seed}.jsonl"
        open(f, "w").write("\n".join(json.dumps(x) for x in lines) + "\n")
        pl = get_pipeline()
        bid = pl.submit_file(__import__("pathlib").Path(f), source="Bank adapter") if "source" in pl.submit_file.__code__.co_varnames else pl.submit_file(__import__("pathlib").Path(f))
        b = pl.wait(bid, 160)
        print("demo batch", bid, b.get("status"), b.get("counts") or {k: b.get(k) for k in ("received", "accepted", "failed", "duplicates")})


if __name__ == "__main__":
    main()

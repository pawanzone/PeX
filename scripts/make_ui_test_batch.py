#!/usr/bin/env python3
"""Write a batch JSON-lines file for manually testing the UI upload (Batches > Upload batch file).

The file uses the generated demo format (same as scripts/gen_synthetic_batch.py) and contains, on purpose:
  44 valid records, 1 possible duplicate (same reference/amount/creditor, new ids -> "Needs review"),
  2 records with an unknown exception type (-> Rejected), 2 exact duplicates inside the file (-> Duplicate).
Ids are unique per run (--salt), so you can upload it many times.

Usage: python scripts/make_ui_test_batch.py [--out ui_test_batch.jsonl] [--seed 11] [--salt demo1]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.synthetic_batch import generate_records  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ui_test_batch.jsonl")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--salt", default=None, help="default: current time, so every run has fresh ids")
    a = ap.parse_args()
    salt = a.salt or time.strftime("%H%M%S")
    try:
        recs = list(generate_records(44, seed=a.seed, salt=salt, tag=f"S{a.seed}-{salt}"))
    except TypeError:
        recs = list(generate_records(44, seed=a.seed))
    dup = json.loads(json.dumps(recs[0]))
    dup["exception_id"] += "-B"
    dup["payment_info"]["payment_id"] += "-B"
    dup["payment_info"]["uetr"] = "9d1c2a40-0b1e-4c1c-8f00-" + f"{a.seed:06d}{salt}"[-12:].rjust(12, "0")
    bad = [dict(recs[1], exception_id=recs[1]["exception_id"] + f"-X{i}", profile_id="ZZ-99") for i in range(2)]
    lines = recs + [dup] + bad + [recs[2], recs[3]]
    Path(a.out).write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    print(f"wrote {len(lines)} records -> {a.out}")
    print("expect: 49 received = about 43-44 accepted + 2 duplicate + 2 rejected + 1-2 needs review (reconciliation must balance)")


if __name__ == "__main__":
    main()

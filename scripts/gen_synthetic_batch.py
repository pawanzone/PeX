#!/usr/bin/env python3
"""CLI: generate a deterministic synthetic payment-exception batch.

Examples:
  python scripts/gen_synthetic_batch.py --count 100000 --seed 7 --out batch_io/inbox/big.jsonl
  python scripts/gen_synthetic_batch.py --count 5000 --rails EU --out /tmp/eu.json.gz
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.synthetic_batch import write_batch  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rails", default="GB,US,EU", help="comma list of GB,US,EU")
    ap.add_argument("--out", required=True, help=".jsonl | .ndjson | .json (envelope) | .jsonl.gz | .json.gz")
    ap.add_argument("--duplicate-rate", type=float, default=0.0)
    ap.add_argument("--malformed-rate", type=float, default=0.0)
    ap.add_argument("--salt", default=None, help="make ids/UETRs unique per run while staying deterministic for (seed, salt)")
    a = ap.parse_args()
    out = write_batch(Path(a.out), a.count, a.seed, a.rails.split(","),
                      duplicate_rate=a.duplicate_rate, malformed_rate=a.malformed_rate, salt=a.salt,
                      tag=(f"S{a.seed}-{a.salt}" if a.salt else None))
    print(f"wrote {a.count} records -> {out} ({out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()

"""Value model: what straight-through handling is worth, from the bank's own inputs.

Plain arithmetic, shown with its assumptions. No PeX price is assumed. When shadow results are loaded, one extra scenario uses the share of cases
PeX would have released, and says whether wrong releases still exist.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.v2.core import V2Error

LIMITS = {"monthly_exceptions": (1, 1_000_000), "minutes_per_case": (0.5, 480), "cost_per_hour": (1, 1000), "review_minutes": (0, 480)}
LABEL = {"monthly_exceptions": "Exceptions per month", "minutes_per_case": "Minutes to handle one case today", "cost_per_hour": "Loaded cost per hour", "review_minutes": "Minutes a person spends approving a case PeX has prepared"}
SHARES = (0.2, 0.4, 0.6)
ASSUMPTIONS = [
    "Saving per case = minutes handled today minus minutes to approve a case PeX has prepared. If approving takes as long as handling, the saving is zero.",
    "The share is the part of all exceptions that PeX prepares and a person approves or that passes straight through. The assumed shares are examples, not forecasts.",
    "Loaded cost per hour is the bank's own figure (salary plus overhead). Currency is the bank's own; nothing is converted.",
    "The model leaves out PeX licence, integration and run cost. It shows the gross saving only; no PeX price is assumed.",
    "Cases that PeX sends to a person (failed a rule, no proposal) are counted as no saving.",
]


def _num(name: str, v: Any) -> float:
    lo, hi = LIMITS[name]
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise V2Error(400, "INVALID", f"{LABEL[name]} must be a number")
    if x != x or x < lo or x > hi:
        raise V2Error(400, "INVALID", f"{LABEL[name]} must be between {lo:g} and {hi:,g}")
    return x


def _row(kind: str, label: str, share: float, i: Dict[str, float], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cases = i["monthly_exceptions"] * share
    hrs = cases * max(0.0, i["minutes_per_case"] - i["review_minutes"]) / 60
    cost = hrs * i["cost_per_hour"]
    r = {"kind": kind, "label": label, "share": round(share, 4), "cases_per_month": round(cases, 1), "hours_saved_month": round(hrs, 1), "cost_saved_month": round(cost, 2),
         "hours_saved_year": round(hrs * 12, 1), "cost_saved_year": round(cost * 12, 2)}
    r.update(extra or {})
    return r


def model(monthly_exceptions: Any, minutes_per_case: Any, cost_per_hour: Any, review_minutes: Any) -> Dict[str, Any]:
    from app.services.v2 import shadow
    i = {"monthly_exceptions": _num("monthly_exceptions", monthly_exceptions), "minutes_per_case": _num("minutes_per_case", minutes_per_case),
         "cost_per_hour": _num("cost_per_hour", cost_per_hour), "review_minutes": _num("review_minutes", review_minutes)}
    rows: List[Dict[str, Any]] = [_row("assumed", f"{int(s * 100)}% of cases", s, i) for s in SHARES]
    sc = shadow.scorecard()
    mpc = None
    if sc["compared"]:
        w = sc["release"]
        wrong = w["released_wrongly"]["count"]
        caveat = (f"{wrong} wrong release(s): cases PeX would have released that the analyst handled differently. Treat this figure as not yet safe until that is zero."
                  if wrong else "No case PeX would have released was handled differently by the analyst in this sample.")
        rows.append(_row("measured", "Measured in shadow", w["would_release"] / sc["compared"], i, {"wrong_releases": wrong, "caveat": caveat, "sample_size": sc["compared"]}))
        t = sc["time"]
        mpc = round(t["minutes_all"] / t["cases_with_minutes"], 1) if t["cases_with_minutes"] else None
    return {"inputs": {k: (int(v) if k == "monthly_exceptions" else v) for k, v in i.items()}, "scenarios": rows, "measured_minutes_per_case": mpc, "assumptions": ASSUMPTIONS}

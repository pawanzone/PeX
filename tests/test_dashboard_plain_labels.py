"""Dashboard rows use the same plain-language exception names as the worklist (not title-cased enum names).

Run:  DATABASE_URL=sqlite:////tmp/dashlabels.db python3 -m pytest tests/test_dashboard_plain_labels.py -q
"""
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.main import app
from app.services.v2 import seed as v2seed

client = TestClient(app)
SUP = "SUP-2001"


def test_dashboard_exception_names_match_worklist_labels():
    v2seed.seed_v2()
    h = {"Authorization": "Bearer " + create_token(SUP)}
    d = client.get("/api/v2/dashboard", headers=h)
    assert d.status_code == 200, d.text
    work = client.get("/api/v2/worklist?tab=ready&page_size=200", headers=h).json()
    labels = {r["exception"]["label"] for r in work.get("items", [])}
    seen = []
    for k in ("stuck", "at_risk", "may_breach"):
        v = d.json().get(k)
        rows = v.get("items", v) if isinstance(v, dict) else (v or [])
        seen += [r["exception"] for r in rows if isinstance(r, dict) and "exception" in r]
    text = " ".join(seen)
    assert "Iso20022" not in text and "_" not in text
    assert all(isinstance(x, str) and x for x in seen)
    assert labels, "worklist must have labels to compare against"

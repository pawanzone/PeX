"""Evidence zone: real values stay inside, tokens and derived facts come out.

Covers classification and role reveal rules, sealing, simulated vs real connectors, stored evidence, audit, notifications,
the AI input and its guard, class-aware reveal (C3 compliance only), reveal after a vault restart, and an end-to-end leak sweep.

Run:  DATABASE_URL=sqlite:////tmp/v2test.db python3 -m pytest tests/test_evidence_zone.py -q
"""
import json

import pytest

from app.config import settings
from app.core.auth import create_token
from app.core.tokenization import token_vault
from app.db.models import AuditEventModel, V2NotificationModel
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import classification as cl
from app.services.v2 import ext as xt
from app.services.v2 import seed as v2seed
from app.services.v2 import zone
from app.services.v2.core import ext_store, iso, now

MAKER, SUP, APPR, CMP, AUD, ADM = "OP-9012", "SUP-2001", "APR-3192", "CMP-6001", "AUD-5001", "ADM-0002"
NAMED = ["PEX-INV-0001", "PEX-INV-0002", "PEX-CON-0031", "PEX-NAM-0027", "PEX-LOW-0096"]


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def get(client, uid, path):
    r = client.get("/api/v2" + path, headers=H(uid))
    assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"
    return r.json()


def post(client, uid, path, body=None, expect=200):
    r = client.post("/api/v2" + path, json=body or {}, headers=H(uid))
    assert r.status_code == expect, f"{path} -> {r.status_code} {r.text}"
    return r.json()


def reveal(client, uid, case_id):
    post(client, uid, f"/cases/{case_id}/pii/reveal", {"reason": "Checking this case against the source documents"})


def raws(case_id):
    """Real values of one case (names and every spelling of its IBANs), as they would appear if they leaked."""
    c = repo.get_case(case_id)
    out = {c["creditor_party"]["party_name"], c["debtor_party"]["party_name"]}
    for k in ("debtor_account", "creditor_account"):
        for v in (c.get(k) or {}).values():
            if isinstance(v, str) and len(v) >= 12 and not v.isalpha():
                out |= {v, xt.iban_compact(v), xt.iban_group(v)}
    ext = ext_store.get(case_id) or {}
    for side in ("original", "proposed"):
        v = ((ext.get("change") or {}).get(side) or {}).get("value")
        if v:
            out |= {v, xt.iban_compact(v), xt.iban_group(v)}
    return {x for x in out if x}


def assert_clean(text, case_id, where):
    for r in raws(case_id):
        assert r not in text, f"real value {r!r} leaked in {where} for {case_id}"


# ---------------------------------------------------------------------------------------------------- classification
def test_role_reveal_matrix():
    assert cl.revealable_classes("ADMIN") == frozenset()
    assert "C3" in cl.revealable_classes("COMPLIANCE_APPROVER")
    for role in ("OPERATOR", "SUPERVISOR", "OPERATIONS_APPROVER", "RISK_APPROVER", "AUDIT_RISK"):
        assert cl.revealable_classes(role) >= {"C1", "C2"} and "C3" not in cl.revealable_classes(role)
    assert {"C1", "C2"} <= cl.revealable_classes("COMPLIANCE_APPROVER")


def test_token_and_field_classes():
    assert cl.token_class("TOK-PARTY-ABCDEF123456") == "C1" and cl.token_class("TOK-SCRN-ABCDEF123456") == "C3"
    assert cl.token_class("TOK-TEXT-ABCDEF123456") == "C2" and cl.token_class("TOK-REF-ABCDEF123456") == "C4"
    assert cl.classify_field("Cdtr.Nm") == "C1" and cl.classify_field("RmtInf.Ustrd") == "C2"
    assert cl.classify_field("sanctions_hit") == "C3" and cl.classify_field("UETR") == "C4" and cl.classify_field("currency") == "C5"


def test_amount_is_banded():
    assert cl.amount_band(8650, "GBP") == "1k to 10k GBP" and cl.amount_band(412000, "EUR") == "250k to 1M EUR"
    assert cl.amount_band(5_000_000, "USD") == "over 1M USD" and cl.amount_band(None) == "unknown"


# ---------------------------------------------------------------------------------------------------- sealing
def test_seal_text_known_values_ibans_and_emails_and_is_idempotent():
    case = repo.get_case("PEX-CON-0031")
    name = case["creditor_party"]["party_name"]
    other = xt.iban_group(xt.make_iban("FR", "30006000011234567890189")) if hasattr(xt, "make_iban") else "FR14 2004 1010 0505 0001 3M02 606"
    s = zone.seal_text(f"Pay {name} at {other}, mail ops@hartmann-it.de", case)
    assert name not in s and other not in s and "ops@hartmann-it.de" not in s
    assert s.count("TOK-PARTY-") == 1 and s.count("TOK-IBAN-") == 1 and s.count("TOK-EMAIL-") == 1
    assert zone.seal_text(s, case) == s                       # tokens are never tokenised again


def test_guard_blocks_real_values_and_passes_tokens():
    case = repo.get_case("PEX-INV-0001")
    with pytest.raises(zone.ZoneLeak):
        zone.guard({"x": f"beneficiary {case['creditor_party']['party_name']}"}, case)
    with pytest.raises(zone.ZoneLeak):
        zone.guard({"x": "GB29 NWBK 6016 1331 9268 19"}, case)
    with pytest.raises(zone.ZoneLeak):
        zone.guard({"x": "a.b@bank.com"}, case)
    assert zone.guard({"x": zone.tok("Someone", "PARTY")}, case)


# ---------------------------------------------------------------------------------------------------- connectors
def test_simulated_is_the_default_and_real_fails_closed(monkeypatch):
    case = repo.get_case("PEX-CON-0031")
    assert all(c["mode"] == "simulated" for c in zone.connector_status())
    monkeypatch.setattr(settings, "CONNECTOR_MODES", "CUSTM=real", raising=False)
    with pytest.raises(zone.ConnectorNotConfigured):
        zone.run("directory", "ev-1", case, {}, iso(now()))


def test_real_adapter_plugs_in_through_the_same_interface(monkeypatch):
    case = repo.get_case("PEX-CON-0031")
    seen = {}

    class Real(zone.Connector):
        key = "CUSTM"

        def fetch(self, req, world):
            seen["req"] = req
            return {"Cdtr": {"Nm": "x"}, "CdtrAcct": {"Id": {"IBAN": "DE89370400440532013000"}}}

    monkeypatch.setattr(settings, "CONNECTOR_MODES", "CUSTM=real", raising=False)
    monkeypatch.setitem(zone.REAL_ADAPTERS, "CUSTM", lambda: Real())
    row = zone.run("directory", "ev-1", case, {}, iso(now()))
    assert row["mode"] == "real" and "TOK-IBAN-" in row["result"] and "DE89" not in json.dumps(row)
    assert seen["req"]["iban"]                                 # real values go in; only tokens come out


def test_checks_return_tokens_and_derived_facts_only():
    c = repo.get_case("PEX-NAM-0027")
    row = zone.run("vop", "ev-1", c, {"account_holder": "V. d. Berg Vastgoed BV"}, iso(now()))
    assert row["facts"]["scheme_result"] == "NMTC" and 0 < row["facts"]["similarity"] < 0.75
    assert "Berg Vastgoed" not in json.dumps(row) and "TOK-PARTY-" in row["result"]
    assert row["fields"][0]["class"] == "C1"
    s = zone.run("screening", "ev-9", c, {"screening": {"hit": True, "list": "EU", "name": "Berg Vastgoed Holdings", "score": 0.91}}, iso(now()))
    assert s["fields"][0]["class"] == "C3" and "Berg Vastgoed Holdings" not in json.dumps(s) and "TOK-SCRN-" in s["result"]


# ---------------------------------------------------------------------------------------------------- stored data
@pytest.mark.parametrize("cid", NAMED)
def test_stored_evidence_holds_no_real_values(cid):
    ext = ext_store.get(cid)
    blob = json.dumps({k: ext.get(k) for k in zone.SEALED_EXT_KEYS})
    assert_clean(blob, cid, "stored evidence")


def test_conflict_case_shows_both_ibans_as_tokens_and_reveal_shows_them(client):
    base = json.dumps(get(client, APPR, "/cases/PEX-CON-0031/page"))
    ext = ext_store.get("PEX-CON-0031")
    inv_iban = next(s["value"] for s in ext["conflict"]["sources"] if s["name"].startswith("Invoice"))
    assert inv_iban.startswith("TOK-IBAN-") and "TOK-IBAN-" in base
    assert_clean(base, "PEX-CON-0031", "page")
    reveal(client, APPR, "PEX-CON-0031")
    shown = json.dumps(get(client, APPR, "/cases/PEX-CON-0031/page"))
    inv_real = xt.iban_group(zone.reveal_value(inv_iban))
    assert inv_real in shown                                  # the invoice IBAN is real again for the person who revealed
    assert get(client, SUP, "/cases/PEX-CON-0031/page")["pii"]["protected"] is True and inv_real not in json.dumps(get(client, SUP, "/cases/PEX-CON-0031/page"))


def test_reveal_still_works_after_a_vault_restart(client):
    ext = ext_store.get("PEX-CON-0031")
    inv_iban = next(s["value"] for s in ext["conflict"]["sources"] if s["name"].startswith("Invoice"))
    real = xt.iban_group(zone.reveal_value(inv_iban))
    zone._display.clear()
    token_vault._token_to_raw.clear()
    token_vault._raw_to_token.clear()                          # as if the process had restarted: only the database remains
    reveal(client, APPR, "PEX-CON-0031")
    assert real in json.dumps(get(client, APPR, "/cases/PEX-CON-0031/page"))


def test_screening_details_reveal_for_compliance_only(client):
    cid = "PEX-NAM-0027"
    c = repo.get_case(cid)
    ext = ext_store.get(cid)
    ext["evidence"].append(zone.run("screening", "ev-9", c, {"screening": {"hit": True, "list": "EU", "name": "Berg Vastgoed Holdings", "score": 0.91}}, iso(now())))
    ext_store.put(cid, ext)
    reveal(client, APPR, cid)
    reveal(client, CMP, cid)
    ops = json.dumps(get(client, APPR, f"/cases/{cid}/page"))
    cmp_ = json.dumps(get(client, CMP, f"/cases/{cid}/page"))
    assert "Berg Vastgoed Holdings" not in ops and "TOK-SCRN-" in ops          # C3 stays a token for operations roles
    assert "Berg Vastgoed Holdings" in cmp_                                       # compliance sees C3
    assert c["creditor_party"]["party_name"] in cmp_ and c["creditor_party"]["party_name"] in ops   # C1 for both


def test_admin_and_audit_rules(client):
    post(client, ADM, "/cases/PEX-INV-0001/pii/reveal", {"reason": "I would like to look at this"}, expect=403)
    post(client, AUD, "/cases/PEX-INV-0001/pii/reveal", {"reason": "Audit sample 2026-10 for control test"})
    ev = get(client, AUD, "/audit/events?case_id=PEX-INV-0001")
    assert any("PII_REVEALED" in json.dumps(e) for e in ev["items"] if isinstance(e, dict)) or "PII_REVEALED" in json.dumps(ev)


# ---------------------------------------------------------------------------------------------------- audit, notifications, AI
@pytest.mark.parametrize("cid", NAMED)
def test_stored_audit_rows_hold_no_real_values(cid):
    db = SessionLocal()
    try:
        rows = db.query(AuditEventModel).filter(AuditEventModel.case_id == cid).all()
        assert rows
        for e in rows:
            assert_clean(str(e.details), cid, "stored audit details")
    finally:
        db.close()


def test_actions_write_tokenised_audit_and_notifications(client):
    cid = "PEX-INV-0002"
    post(client, MAKER, f"/cases/{cid}/submit", {"handover_note": "Client confirmed by phone"})
    post(client, APPR, f"/cases/{cid}/return", {"reviewed": True, "reason_code": "EVIDENCE_INSUFFICIENT", "comment": f"Please re-check {repo.get_case(cid)['creditor_party']['party_name']} against the invoice."})
    db = SessionLocal()
    try:
        for e in db.query(AuditEventModel).filter(AuditEventModel.case_id == cid).all():
            assert_clean(str(e.details), cid, "audit")
        for n in db.query(V2NotificationModel).filter(V2NotificationModel.case_id == cid).all():
            assert_clean(f"{n.title} {n.text}", cid, "notification")
    finally:
        db.close()


def test_ai_view_has_tokens_band_and_facts_only(client):
    cid = "PEX-INV-0001"
    v = get(client, APPR, f"/cases/{cid}/ai-view")
    blob = json.dumps(v["payload"])
    assert_clean(blob, cid, "ai view")
    assert v["payload"]["case"]["amount_band"] == "1k to 10k GBP" and "8650" not in blob
    assert v["payload"]["parties"]["creditor"].startswith("TOK-PARTY-") and v["payload"]["reference"].startswith("TOK-REF-")
    assert v["guard"]["passed"] is True
    assert any(e["facts"] for e in v["payload"]["evidence"])


@pytest.mark.parametrize("cid", NAMED)
def test_llm_input_guard_passes_for_every_named_case(cid):
    case = repo.get_case(cid)
    assert zone.llm_input(case, ext_store.get(cid))


def test_ai_view_stays_tokenised_even_during_a_reveal(client):
    cid = "PEX-INV-0001"
    reveal(client, APPR, cid)
    assert_clean(json.dumps(get(client, APPR, f"/cases/{cid}/ai-view")["payload"]), cid, "ai view during reveal")


# ---------------------------------------------------------------------------------------------------- integration
def test_choosing_a_candidate_uses_the_real_value_for_the_repair(client):
    cid = "PEX-CON-0031"
    post(client, SUP, f"/cases/{cid}/assign", {"user_id": MAKER}) if False else None
    ext = ext_store.get(cid)
    cands = ext["conflict"]["candidates"]
    assert all(str(c["value"]).startswith("TOK-IBAN-") for c in cands)                  # stored sealed
    post(client, MAKER, f"/cases/{cid}/disambiguate", {"candidate_id": "H-2", "rationale": "Invoice confirmed by client on call"})
    ch = ext_store.get(cid)["change"]
    assert xt.iban_valid(ch["proposed"]["value"]) and not ch["proposed"]["value"].startswith("TOK-")   # the repair carries the real IBAN
    assert ch["proposed"]["value"] != ch["original"]["value"]
    assert "TOK-IBAN-" in json.dumps(get(client, APPR, f"/cases/{cid}/page")["change_summary"])


def test_leak_sweep_across_every_surface(client):
    """Default view of an approver: pages, lists, audit, notifications and AI input hold none of the real values of any named case."""
    surfaces = {"approvals": json.dumps(get(client, APPR, "/approvals")), "audit": json.dumps(get(client, AUD, "/audit/events?page_size=200")),
                "notifications": json.dumps(get(client, APPR, "/notifications"))}
    for cid in NAMED:
        surfaces[f"page {cid}"] = json.dumps(get(client, APPR, f"/cases/{cid}/page"))
        surfaces[f"ai {cid}"] = json.dumps(get(client, APPR, f"/cases/{cid}/ai-view"))
    for where, text in surfaces.items():
        for cid in NAMED:
            assert_clean(text, cid, where)

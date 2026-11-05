"""Integration contract view: what a bank must send, and what PeX can fetch itself. Acceptance tests written from the requirements.

  K1  Admins and Policy Owners can read it; every other role cannot. It is read only.
  K2  Every one of the 41 profiles has a contract: its evidence rows match the pack (type, mandatory, trust tier).
  K3  Every evidence row says how PeX gets it. "PeX looks it up" appears only where a lookup really exists in the registry.
  K4  Rows that could be looked up but have no connector are labelled so; bank-owned data is always "Sent by the bank".
  K5  The envelope (fields the event needs to be accepted) comes from the real input schema.
  K6  The sample event is a real fixture, validates against the real input schema and carries every mandatory evidence type.
  K7  The overview explains single and batch delivery, the four acquisition modes and lists every lookup with real or simulated.
  K8  The wording says the bank's SMEs validate it against their process.
"""
import pytest

from app.core.auth import create_token
from app.profile_packs import registry
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo
from app.services import reference_connectors as rc
from app.services.v2 import semantic_data as sd

PACKS = registry.load_packs()
ALLOWED = ["ADM-0002", "POL-8001", "POL-8002"]
DENIED = ["OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001"]
HOW = {"BANK_SENDS", "PEX_LOOKUP_COMPUTED", "PEX_LOOKUP_SIMULATED", "COULD_LOOK_UP"}
BANK_OWNED = {"BANK_COUNTERPARTY_SSI", "BANK_DESIGNATED_SSI", "CORRESPONDENT_SSI_DIRECTORY", "SYNTAX_ERROR_SPECIFICATION"}


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def get(client, path, uid="ADM-0002"):
    return client.get(f"/api/v2/reference/{path}", headers=H(uid))


@pytest.fixture()
def all_contracts(client):
    return {c: get(client, f"contract/{c}").json() for c in PACKS}


# K1 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("path", ["contract", "contract/DQ-01"])
def test_k1_access(client, path):
    for u in ALLOWED:
        assert get(client, path, u).status_code == 200
    for u in DENIED:
        assert get(client, path, u).status_code == 403
    for verb in (client.post, client.put, client.delete):
        assert verb(f"/api/v2/reference/{path}", headers=H()).status_code in (404, 405)


def test_k1_unknown_profile_is_404(client):
    assert get(client, "contract/DQ-99").status_code == 404


# K2 -------------------------------------------------------------------------------------------------------------
def test_k2_every_profile_matches_its_pack(all_contracts):
    assert len(all_contracts) == 41
    for code, d in all_contracts.items():
        pack = PACKS[code]
        rows = {r["type"]: r for r in d["evidence"]}
        assert set(rows) == {e.type for e in pack.evidence.required}, code
        for e in pack.evidence.required:
            r = rows[e.type]
            assert r["mandatory"] is e.mandatory and r["tier"] == e.tier and r["tier_name"], (code, e.type)
            assert r["meaning"] and r["source_system"] and r["category"] and r["freshness_hours"] == 24
        assert d["code"] == code and d["name"] and d["validation_status"] == "Bank SME to validate against their process"
        assert d["counts"]["mandatory"] == sum(e.mandatory for e in pack.evidence.required)
        assert d["counts"]["total"] == len(pack.evidence.required)


# K3, K4 ---------------------------------------------------------------------------------------------------------
def test_k3_lookup_claims_match_the_registry_exactly(all_contracts):
    seen = set()
    for code, d in all_contracts.items():
        for r in d["evidence"]:
            assert r["how"] in HOW, (code, r["how"])
            in_reg = r["type"] in rc.REGISTRY
            assert (r["how"] in ("PEX_LOOKUP_COMPUTED", "PEX_LOOKUP_SIMULATED")) == in_reg, (code, r["type"])
            if in_reg:
                c = rc.REGISTRY[r["type"]]
                assert r["lookup"]["kind"] == c.kind and r["lookup"]["source"] == c.source and r["lookup"]["as_of"] == c.as_of and r["lookup"]["params"] == list(c.params)
                assert r["how"] == ("PEX_LOOKUP_COMPUTED" if c.kind == "COMPUTED" else "PEX_LOOKUP_SIMULATED")
                assert "MODE_2_API_CONNECTOR" in r["modes"]
                seen.add(r["type"])
            else:
                assert r["lookup"] is None and "MODE_2_API_CONNECTOR" not in r["modes"]
    assert seen, "at least one profile uses a built lookup"


def test_k4_could_look_up_and_bank_owned(all_contracts):
    for code, d in all_contracts.items():
        for r in d["evidence"]:
            if r["type"] in BANK_OWNED:
                assert r["how"] == "BANK_SENDS", r["type"]
            if r["how"] == "COULD_LOOK_UP":
                assert r["category"] == sd.EVIDENCE[r["type"]][0] == "Reference data" and r["type"] not in rc.REGISTRY and r["type"] not in BANK_OWNED
            if r["category"] != "Reference data":
                assert r["how"] == "BANK_SENDS", (code, r["type"])
            assert {"MODE_1_INBOUND_PAYLOAD", "MODE_3_BANK_PUSH", "MODE_4_HITL_OPERATOR"} <= set(r["modes"])
    labels = {r["how_label"] for d in all_contracts.values() for r in d["evidence"]}
    assert len(labels) >= 3 and all(labels)


# K5 -------------------------------------------------------------------------------------------------------------
def test_k5_envelope_comes_from_the_input_schema(client):
    d = get(client, "contract").json()
    req = {n for n, f in E2EPaymentInfo.model_fields.items() if f.is_required()}
    env = {e["field"]: e for e in d["envelope"]["payment_fields"]}
    assert {n for n, e in env.items() if e["required"]} == req == {"payment_id", "uetr", "amount", "currency", "clearing_rail"}
    assert set(env) == set(E2EPaymentInfo.model_fields) and all(e["meaning"] for e in env.values())
    assert {"exception_id", "payment_info"} <= {e["field"] for e in d["envelope"]["top_fields"] if e["required"]}
    assert [g["field"] for g in d["envelope"]["evidence_groups"]] == ["bank_supplied_evidence", "external_authoritative_evidence", "derived_evidence", "historical_evidence"]


def test_k5_profile_payment_fields_are_marked_for_sme_validation(all_contracts):
    for code, d in all_contracts.items():
        pf = d["payment_fields"]
        assert {"always_required", "used_in_sample", "note"} <= set(pf)
        assert set(pf["always_required"]) == {"payment_id", "uetr", "amount", "currency", "clearing_rail"}
        assert "validate" in pf["note"].lower()
        assert set(pf["used_in_sample"]) <= set(E2EPaymentInfo.model_fields)


# K6 -------------------------------------------------------------------------------------------------------------
def test_k6_samples_are_real_valid_and_complete(all_contracts):
    missing = []
    for code, d in all_contracts.items():
        s = d["sample"]
        if s is None:
            missing.append(code)
            assert d["sample_note"]
            continue
        ev = s["event"]
        CanonicalE2EInput.model_validate(ev)
        assert ev["profile_id"] == code and s["file"].endswith(".json") and s["synthetic"] is True
        have = {k.lower() for b in ("bank_supplied_evidence", "external_authoritative_evidence", "derived_evidence", "historical_evidence") for k in (ev.get(b) or {})}
        for e in PACKS[code].evidence.required:
            if e.mandatory:
                assert e.type.lower() in have, (code, e.type)
    assert set(missing) <= {"DQ-05"}


# K7 -------------------------------------------------------------------------------------------------------------
def test_k7_overview(client):
    d = get(client, "contract").json()
    assert d["profiles"] == 41 and len(d["coverage"]) == 41
    assert [m["mode"] for m in d["modes"]] == ["MODE_1_INBOUND_PAYLOAD", "MODE_2_API_CONNECTOR", "MODE_3_BANK_PUSH", "MODE_4_HITL_OPERATOR"] and all(m["meaning"] for m in d["modes"])
    assert {x["kind"] for x in d["lookups"]} == {"COMPUTED", "SIMULATED_DIRECTORY"} and len(d["lookups"]) == 9
    assert sum(x["kind"] == "COMPUTED" for x in d["lookups"]) == 5
    assert all(x["name"] and x["source"] and x["as_of"] and x["used_by_profiles"] is not None for x in d["lookups"])
    assert {"single", "batch"} <= set(d["delivery"]) and d["delivery"]["batch"]["outcomes"] == ["PROCESSED", "SKIPPED_EXISTING_CASE", "SKIPPED_DUPLICATE_IN_BATCH", "FAILED_SCHEMA", "FAILED_PROCESSING"]
    assert d["evidence_summary"]["distinct_types"] == len({e.type for p in PACKS.values() for e in p.evidence.required})
    assert d["evidence_summary"]["shared_by_two_or_more"] == sum(1 for t in {e.type for p in PACKS.values() for e in p.evidence.required} if sum(any(e.type == t for e in p.evidence.required) for p in PACKS.values()) >= 2)
    assert d["validation_status"] == "Bank SME to validate against their process" and d["rule"]
    cov = {c["code"]: c for c in d["coverage"]}
    assert set(cov) == set(PACKS) and all(c["mandatory"] <= c["total"] and c["lookups_built"] <= c["total"] for c in cov.values())


def test_k8_the_overview_is_honest_about_simulation(client):
    d = get(client, "contract").json()
    assert "simulated" in d["rule"].lower()
    assert all(x["kind"] == "COMPUTED" or "simulated" in x["source"].lower() for x in d["lookups"])

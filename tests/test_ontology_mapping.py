"""The Payment ontology tab and the canonical data model describe the same thing, and a test keeps them from drifting.

  M1  Every key field of every ontology entity has a mapping: a canonical field, a derivation from canonical fields, or both noted honestly.
  M2  Every canonical home and every derivation source exists in the code.
  M3  Each ontology entity links to a logical-model entity that is in code.
  M4  The context entities (client, KYC, treasury, precedent) are real canonical models and are in the semantic layer.
  M5  The API returns the mapping per field and says which entities are simulated in the demo.
  M6  No logical entity is left as planned.
"""
import pytest

from app.core.auth import create_token
from app.schemas import canonical as cn


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def onto(client):
    return client.get("/api/v2/reference/ontology", headers=H()).json()


def resolves(path):
    m, _, f = path.partition(".")
    c = getattr(cn, m, None)
    return c is not None and (not f or f in c.model_fields)


def test_m1_every_ontology_field_is_mapped(client):
    d = onto(client)
    assert len(d["entities"]) == 7
    for e in d["entities"]:
        assert [f["name"] for f in e["fields"]] == e["key_fields"], e["name"]
        for f in e["fields"]:
            assert f["kind"] in ("canonical", "derived"), (e["name"], f["name"])
            assert f["home"] if f["kind"] == "canonical" else f["derived_from"], (e["name"], f["name"])


def test_m2_homes_and_sources_exist_in_code(client):
    for e in onto(client)["entities"]:
        for f in e["fields"]:
            for p in ([f["home"]] if f["kind"] == "canonical" else f["derived_from"]):
                assert resolves(p), (e["name"], f["name"], p)
            assert f["in_code"] is True


def test_m3_each_entity_links_to_an_entity_in_code(client):
    lm = {x["name"]: x for x in client.get("/api/v2/reference/data-model", headers=H()).json()["logical_model"]["entities"]}
    for e in onto(client)["entities"]:
        assert e["logical_entity"] in lm and lm[e["logical_entity"]]["status"] == "in code", e["name"]


@pytest.mark.parametrize("name,fields", [
    ("CanonicalCustomer", ["client_id", "name", "client_type", "segment", "country", "risk_rating", "service_tier", "historical_exception_rate", "stp_repair_eligible"]),
    ("CanonicalKycRecord", ["client_id", "status", "risk_classification", "expired_documents", "missing_documents", "payment_restriction"]),
    ("CanonicalTreasuryPosition", ["correspondent_bic", "currency", "nostro_balance", "liquidity_threshold", "currency_shortfall", "funding_route_available"]),
    ("CanonicalPrecedentSummary", ["case_match_count", "average_similarity", "last_resolution_action", "settlement_success_rate"]),
])
def test_m4_context_entities_are_models_and_in_the_semantic_layer(name, fields):
    from app.services.v2 import semantic_layer as sl
    assert list(getattr(cn, name).model_fields) == fields
    keys = {r["canonical"] for r in sl.field_mappings()}
    assert name in sl.MODELS and all(f"{name}.{f}" in keys for f in fields)


def test_m4b_models_build_and_default_safely():
    k = cn.CanonicalKycRecord(client_id="C1", status="ACTIVE", risk_classification="LOW")
    assert k.expired_documents == [] and k.missing_documents == [] and k.payment_restriction is False
    t = cn.CanonicalTreasuryPosition(correspondent_bic="CITIGB2L", currency="EUR", nostro_balance=1.0)
    assert t.currency_shortfall is None and t.funding_route_available is None


def test_m5_api_flags_simulated_entities(client):
    d = onto(client)
    sim = {e["name"]: e["source_note"] for e in d["entities"]}
    for n in ("Client", "KYC", "Treasury", "Historical Cases"):
        assert "simulated" in sim[n].lower(), n
    assert "simulated" not in sim["Payment"].lower()
    assert "derived" in d["note"].lower() or "canonical" in d["note"].lower()


def test_m6_nothing_is_planned(client):
    lm = client.get("/api/v2/reference/data-model", headers=H()).json()["logical_model"]
    assert lm["planned_names"] == []

"""Read-only reference pages for Administrators and Policy Owners: Payment Ontology, Canonical DB and Semantic Layer, SOP list.

  R1  Administrators and Policy Owners can read them; every other role cannot.
  R2  They are read only.
  R3  The data model is read from the real database models and canonical schemas, so it cannot drift from the code.
  R4  The semantic layer maps canonical fields to ISO 20022 elements, and every mapped field really exists.
  R5  The SOP list covers every exception profile the platform handles, with its evidence items.
"""
import pytest

from app.core.auth import create_token
from app.db.base import Base
from app.schemas import canonical as cn
from app.services.v2 import evidence_model as em

ALLOWED = ["ADM-0002", "POL-8001", "POL-8002"]
DENIED = ["OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001"]


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


def get(client, path, uid="ADM-0002"):
    return client.get(f"/api/v2/reference/{path}", headers=H(uid))


@pytest.mark.parametrize("path", ["ontology", "data-model", "sops"])
@pytest.mark.parametrize("uid", ALLOWED)
def test_admin_and_policy_owner_can_read(client, path, uid):
    assert get(client, path, uid).status_code == 200


@pytest.mark.parametrize("path", ["ontology", "data-model", "sops"])
@pytest.mark.parametrize("uid", DENIED)
def test_everyone_else_cannot(client, path, uid):
    assert get(client, path, uid).status_code == 403


@pytest.mark.parametrize("path", ["ontology", "data-model", "sops"])
def test_read_only(client, path):
    for verb in (client.post, client.put, client.delete):
        assert verb(f"/api/v2/reference/{path}", headers=H("ADM-0002")).status_code in (404, 405)


def test_ontology_has_the_pipeline_and_entities(client):
    d = get(client, "ontology").json()
    assert len(d["pipeline"]) == 6 and len(d["entities"]) >= 7 and d["domains"]
    assert all(e["name"] and e["standard"] and e["key_fields"] for e in d["entities"])


def test_data_model_comes_from_the_real_tables(client):
    d = get(client, "data-model").json()
    names = {t["name"] for t in d["tables"]}
    assert names == set(Base.metadata.tables)
    t = next(t for t in d["tables"] if t["name"] == "v2_policy_changes")
    cols = {c["name"]: c for c in t["columns"]}
    assert cols["id"]["primary_key"] and "status" in cols
    fks = [(r["from"], r["to"]) for r in d["relations"]]
    for tbl in Base.metadata.tables.values():
        for fk in tbl.foreign_keys:
            assert (f"{tbl.name}.{fk.parent.name}", fk.target_fullname) in fks


def test_canonical_models_are_listed_with_their_fields(client):
    d = get(client, "data-model").json()
    m = {x["name"]: x for x in d["canonical"]}
    assert {"CanonicalParty", "CanonicalAccount", "CanonicalPayment", "CanonicalException"} <= set(m)
    assert {f["name"] for f in m["CanonicalAccount"]["fields"]} == set(cn.CanonicalAccount.model_fields)


def test_semantic_layer_maps_real_fields_to_iso(client):
    d = get(client, "data-model").json()
    sl = d["semantic_layer"]
    assert len(sl) >= 15
    for m in sl:
        model, field = m["canonical"].split(".")
        assert field in getattr(cn, model).model_fields, m["canonical"]
        assert m["iso20022"] and m["description"]
    assert any("IBAN" in m["iso20022"] for m in sl) and any("UETR" in m["iso20022"] for m in sl)


def test_sop_list_covers_every_profile(client):
    d = get(client, "sops").json()
    assert d["total"] == len(em.PROFILES) == len(d["items"])
    row = d["items"][0]
    assert row["code"] in em.PROFILES and row["name"] and row["standards"] and row["evidence_items"] >= 3 and row["status"] and row["version"]
    one = get(client, f"sops/{row['code']}").json()
    assert one["code"] == row["code"] and sum(i["weight"] for i in one["items"]) == 100 and all(i["system_name"] for i in one["items"])


def test_unknown_sop_is_404(client):
    assert get(client, "sops/NOPE-99").status_code == 404

"""The semantic layer is generated from the real models and profile packs, so it cannot drift and it covers what PeX actually uses.

  S1  Every field of the four canonical payment models has a mapping row (ISO 20022 element or an explicit PeX-internal reason).
  S2  Every evidence type any profile pack asks for has a catalogue entry; no catalogue entry is unused.
  S3  "Used by" is computed from the packs (profile, tier), never typed by hand.
  S4  Every row names its data class (C1 to C5), and field rows carry the SWIFT MT equivalent and a validation rule.
  S5  Message elements the profiles rely on but the canonical model does not carry yet are listed openly, and each names real profiles.
  S6  The API exposes the layers, a coverage summary, and keeps the old `semantic_layer` shape.
"""
import json
from pathlib import Path

import pytest

from app.core.auth import create_token
from app.schemas import canonical as cn
from app.services.v2 import classification as cls
from app.services.v2 import semantic_layer as sl

PACKS = Path(__file__).resolve().parents[1] / "app" / "profile_packs" / "packs"
MODELS = ["CanonicalParty", "CanonicalAccount", "CanonicalPayment", "CanonicalException"]


def packs():
    return {p["code"]: p for p in (json.loads(f.read_text()) for f in sorted(PACKS.glob("*.json")))}


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def test_s1_every_canonical_field_is_mapped():
    rows = sl.field_mappings()
    have = {r["canonical"] for r in rows}
    want = {f"{m}.{f}" for m in MODELS for f in getattr(cn, m).model_fields}
    assert want <= have, sorted(want - have)
    assert have <= want, sorted(have - want)          # nothing mapped that does not exist
    for r in rows:
        assert r["iso20022"] and r["description"]


def test_s2_every_pack_evidence_type_is_catalogued_and_none_orphaned():
    used = {e["type"] for p in packs().values() for e in p["evidence"]["required"]}
    cat = {r["type"] for r in sl.evidence_catalogue()}
    assert used <= cat, sorted(used - cat)
    assert cat <= used, sorted(cat - used)
    assert len(cat) >= 100


def test_s3_used_by_comes_from_the_packs():
    P = packs()
    for r in sl.evidence_catalogue():
        expect = sorted((c, e["tier"]) for c, p in P.items() for e in p["evidence"]["required"] if e["type"] == r["type"])
        assert sorted((u["code"], u["tier"]) for u in r["used_by"]) == expect, r["type"]
        assert r["profile_count"] == len(expect) and expect


def test_s4_data_class_mt_and_validation_present():
    for r in sl.evidence_catalogue():
        assert r["data_class"] in cls.CLASSES, r["type"]
        assert r["category"] and r["source_system"] and r["proves"], r["type"]
    for r in sl.field_mappings():
        assert r["data_class"] in cls.CLASSES, r["canonical"]
        assert r["mt"] and r["validation"], r["canonical"]
    for r in sl.element_catalogue():
        assert r["data_class"] in cls.CLASSES and r["mt"] and r["why"], r["element"]


def test_s5_uncovered_elements_are_listed_with_real_profiles():
    P = packs()
    rows = sl.element_catalogue()
    assert len(rows) >= 30
    for r in rows:
        assert r["in_canonical_model"] is False
        assert r["used_by"] and set(r["used_by"]) <= set(P), r["element"]
    msgs = " ".join(r["message"] for r in rows)
    for m in ("pacs.008", "pacs.002", "pacs.004", "camt.056", "camt.029"):
        assert m in msgs


def test_s6_api_exposes_layers_and_summary(client):
    d = client.get("/api/v2/reference/data-model", headers=H()).json()
    assert len(d["semantic_layer"]) == len(sl.field_mappings())
    assert all("." in m["canonical"] for m in d["semantic_layer"])          # old shape kept
    assert len(d["evidence_catalogue"]) == len(sl.evidence_catalogue())
    assert len(d["element_catalogue"]) == len(sl.element_catalogue())
    s = d["semantic_summary"]
    assert s["canonical_fields_mapped"] == s["canonical_fields_total"] > 0
    assert s["evidence_types"] == len(d["evidence_catalogue"]) and s["profiles"] == len(packs())
    assert s["iso_messages"] and s["categories"]

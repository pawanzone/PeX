"""Routing directory entry: the last "planned" entity becomes a canonical model.

  R1  The model carries BIC, clearing member, institution, status, successors, rails, source and validity dates; optional parts default safely.
  R2  The existing BIC reference directory entry (DQ-02) loads into it with nothing lost.
  R3  A clearing-system routing identifier (DQ-08) loads into it.
  R4  Freshness fails closed: no expiry date, or a past one, means "not current".
  R5  An agent in a payment is looked up against a directory by BIC (8 or 11 characters) and by clearing member.
  R6  The logical model shows no planned entities, the semantic layer maps every field, and the ontology and data-model pages still agree.
"""
from datetime import datetime, timedelta, timezone

from app.core.auth import create_token
from app.schemas import canonical as cn


def test_r1_model_shape_and_defaults():
    assert list(cn.CanonicalRoutingEntry.model_fields) == [
        "bic", "clearing_system_id", "member_id", "institution_name", "country", "status", "is_head_office", "successor_bics", "supported_rails",
        "source", "retrieved_at", "effective_at", "expires_at"]
    e = cn.CanonicalRoutingEntry(status="ACTIVE")
    assert e.bic is None and e.member_id is None and e.successor_bics == [] and e.supported_rails == [] and e.expires_at is None


def test_r2_bic_reference_entry_loads_with_nothing_lost():
    from app.services import iso_canonical as ic
    from app.services.dq02_bic_resolver import BICReferenceEntry, BICStatus
    now = datetime.now(timezone.utc)
    ref = BICReferenceEntry(bic_code="DRESDEFFXXX", status=BICStatus.REPLACED, institution_name="Dresdner Bank", country_code="DE", location_code="FF",
                            branch_code="XXX", is_head_office=True, successor_bics=["COBADEFFXXX"], supported_rails=["SWIFT_CBPR+", "TARGET2"],
                            provider="SWIFTREF", retrieved_at=now, effective_at=now - timedelta(days=30), expires_at=now + timedelta(days=1))
    e = ic.routing_entry_from_bic_reference(ref)
    assert (e.bic, e.status, e.institution_name, e.country, e.is_head_office) == ("DRESDEFFXXX", "REPLACED", "Dresdner Bank", "DE", True)
    assert e.successor_bics == ["COBADEFFXXX"] and e.supported_rails == ["SWIFT_CBPR+", "TARGET2"] and e.source == "SWIFTREF"
    assert e.retrieved_at == now.isoformat() and e.expires_at == (now + timedelta(days=1)).isoformat()


def test_r3_clearing_routing_identifier_loads():
    from app.services import iso_canonical as ic
    e = ic.routing_entry_from_identifier("026009593", "FEDWIRE", institution_name="Bank of America", country="US", source="CENTRAL_BANK_ROUTING_DIRECTORY", status="ACTIVE")
    assert (e.member_id, e.clearing_system_id, e.country, e.status, e.source) == ("026009593", "FEDWIRE", "US", "ACTIVE", "CENTRAL_BANK_ROUTING_DIRECTORY")
    assert e.bic is None


def test_r4_freshness_fails_closed():
    from app.services import iso_canonical as ic
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    fresh = cn.CanonicalRoutingEntry(status="ACTIVE", expires_at=(now + timedelta(hours=1)).isoformat())
    old = cn.CanonicalRoutingEntry(status="ACTIVE", expires_at=(now - timedelta(seconds=1)).isoformat())
    unknown = cn.CanonicalRoutingEntry(status="ACTIVE")
    bad = cn.CanonicalRoutingEntry(status="ACTIVE", expires_at="not a date")
    assert ic.routing_entry_is_current(fresh, now) is True
    assert ic.routing_entry_is_current(old, now) is False and ic.routing_entry_is_current(unknown, now) is False and ic.routing_entry_is_current(bad, now) is False


def test_r5_agent_lookup_by_bic_and_member():
    from app.services import iso_canonical as ic
    a = cn.CanonicalRoutingEntry(bic="COBADEFFXXX", status="ACTIVE")
    b = cn.CanonicalRoutingEntry(clearing_system_id="DEBLZ", member_id="37040044", status="ACTIVE")
    entries = [a, b]
    assert ic.find_routing_entry(cn.CanonicalAgent(role="CREDITOR_AGENT", bic="COBADEFF"), entries) is a
    assert ic.find_routing_entry(cn.CanonicalAgent(role="CREDITOR_AGENT", bic="COBADEFFXXX"), entries) is a
    assert ic.find_routing_entry(cn.CanonicalAgent(role="CREDITOR_AGENT", clearing_system_id="DEBLZ", member_id="37040044"), entries) is b
    assert ic.find_routing_entry(cn.CanonicalAgent(role="CREDITOR_AGENT", bic="ZZZZGB2L"), entries) is None
    assert ic.find_routing_entry(cn.CanonicalAgent(role="CREDITOR_AGENT"), entries) is None  # nothing to match on


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def test_r6_nothing_is_planned_and_everything_is_mapped(client):
    from app.services.v2 import semantic_layer as sl
    d = client.get("/api/v2/reference/data-model", headers=H()).json()
    lm = d["logical_model"]
    e = {x["name"]: x for x in lm["entities"]}["Routing directory entry"]
    assert e["status"] == "in code" and e["canonical_class"] == "CanonicalRoutingEntry" and e["fields"] == 13
    assert lm["summary"]["planned"] == 0 and lm["planned_names"] == []
    keys = {r["canonical"] for r in sl.field_mappings()}
    assert "CanonicalRoutingEntry" in sl.MODELS and all(f"CanonicalRoutingEntry.{f}" in keys for f in cn.CanonicalRoutingEntry.model_fields)

"""Bank outcome, approval and audit event become canonical models (they were "database only").

  O1  Each table's columns are all carried by the canonical model, so model and table cannot drift
      (approval and audit event match their tables exactly).
  O2  The canonical approval and audit classes are the same objects the workflow already uses (no second definition).
  O3  CanonicalBankOutcome maps a pacs.002 status report: accepted/settled, in progress, rejected; anything else yields no outcome (fails closed).
  O4  CanonicalBankOutcome builds from a stored bank_outcomes row and from the signed callback payload, keeping idempotency key and signature flag.
  O5  The logical model shows Bank outcome, Approval and Audit event as in code, and only the three routing/KYC/position entities stay planned.
  O6  Every field of the three models is in the semantic layer with an ISO element or a PeX-internal mark, a validation rule and a data class.
  O7  Existing behaviour is untouched: a signed bank callback still stores a row that loads into the model.
"""
import json

import pytest

from app.core.auth import create_token
from app.db.base import Base
from app.schemas import canonical as cn
import app.db.models  # noqa: F401  (registers the tables)

TABLES = {"bank_outcomes": "CanonicalBankOutcome", "approval_records": "CanonicalApprovalRecord", "audit_events": "CanonicalAuditEvent"}


def test_o1_every_table_column_is_carried_by_the_model():
    for table, model in TABLES.items():
        cols = {c.name for c in Base.metadata.tables[table].columns}
        fields = set(getattr(cn, model).model_fields)
        assert cols <= fields, (table, cols - fields)
        if table != "bank_outcomes":
            assert fields == cols, (table, fields ^ cols)


def test_o2_canonical_approval_and_audit_are_the_workflow_classes():
    from app.schemas.approval import ApprovalRecord
    from app.schemas.audit import AuditEvent
    assert cn.CanonicalApprovalRecord is ApprovalRecord and cn.CanonicalAuditEvent is AuditEvent


def test_o3_pacs002_status_maps_to_a_bank_outcome_and_unknown_fails_closed():
    from app.services import iso_canonical as ic
    def rep(status, reason=None):
        return cn.CanonicalStatusReport(message_type="pacs.002", uetr="dd11ee22-33ff-44aa-55bb-66cc77889900", status=status, reason_code=reason, originator="Deutsche Bank")
    for st, want in (("ACSC", "SETTLED"), ("ACCC", "SETTLED"), ("ACSP", "EXECUTED_CONFIRMED"), ("RJCT", "REJECTED")):
        o = ic.bank_outcome_from_status(rep(st, "AC04" if st == "RJCT" else None), case_id="C1", bank_reference="REF1", clearing_system="CHAPS")
        assert o.outcome == want and o.case_id == "C1" and o.bank_reference == "REF1" and o.status_code == st
        assert o.uetr == "dd11ee22-33ff-44aa-55bb-66cc77889900" and o.idempotency_key
        assert o.signature_verified is False  # a parsed message is not a verified callback
    assert ic.bank_outcome_from_status(rep("RJCT", "AC04"), case_id="C1", bank_reference="R").reason_code == "AC04"
    for bad in ("PDNG", "", None, "WHATEVER"):
        assert ic.bank_outcome_from_status(rep(bad), case_id="C1", bank_reference="R") is None
    assert ic.bank_outcome_from_status(cn.CanonicalStatusReport(message_type="pacs.004", kind="RETURN", status="RTRN"), case_id="C1", bank_reference="R") is None


def test_o4_builds_from_a_stored_row_and_from_the_callback_payload():
    from app.services import iso_canonical as ic
    row = {"idempotency_key": "IDEMP-1", "case_id": "C9", "outcome": "SETTLED", "bank_reference": "B-1", "clearing_system": "TARGET2", "received_at": "2026-11-05T10:00:00+00:00", "signature_verified": True}
    o = ic.bank_outcome_from_row(row)
    assert (o.idempotency_key, o.case_id, o.outcome, o.bank_reference, o.clearing_system, o.signature_verified) == ("IDEMP-1", "C9", "SETTLED", "B-1", "TARGET2", True)
    p = ic.bank_outcome_from_callback({"case_id": "C9", "uetr": "U9", "outcome": " settled ", "bank_reference": "B-2", "clearing_system": "CHAPS"}, signature_verified=True, received_at="2026-11-05T10:00:00+00:00")
    assert p.outcome == "SETTLED" and p.uetr == "U9" and p.signature_verified is True and p.idempotency_key == "IDEMP-BANK-C9-B-2-SETTLED"
    with pytest.raises(ValueError):
        ic.bank_outcome_from_callback({"case_id": "C9", "outcome": "MAYBE", "bank_reference": "B"}, signature_verified=True)


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def test_o5_logical_model_shows_the_three_as_in_code(client):
    lm = client.get("/api/v2/reference/data-model", headers=H()).json()["logical_model"]
    e = {x["name"]: x for x in lm["entities"]}
    for name, klass in (("Bank outcome", "CanonicalBankOutcome"), ("Approval", "CanonicalApprovalRecord"), ("Audit event", "CanonicalAuditEvent")):
        assert e[name]["status"] == "in code" and e[name]["canonical_class"] == klass and e[name]["db_table"] and e[name]["fields"] > 0, name
    assert lm["summary"]["database_only"] == 0
    assert lm["planned_names"] == []


def test_o6_semantic_layer_covers_the_new_models():
    from app.services.v2 import semantic_layer as sl
    keys = {r["canonical"]: r for r in sl.field_mappings()}
    for m in TABLES.values():
        assert m in sl.MODELS
        for f in getattr(cn, m).model_fields:
            r = keys[f"{m}.{f}"]
            assert r["iso20022"] and r["validation"] and r["data_class"] in ("C1", "C2", "C3", "C4", "C5"), (m, f)
    assert keys["CanonicalAuditEvent.current_hash"]["pex_internal"] and keys["CanonicalAuditEvent.details"]["data_class"] == "C2"


def test_o7_a_stored_bank_outcome_row_loads_into_the_model(client):
    from app.db.models import BankOutcomeModel
    from app.db.session import SessionLocal
    from app.services import iso_canonical as ic
    db = SessionLocal()
    try:
        db.merge(BankOutcomeModel(idempotency_key="O7-IDEM", case_id="O7-CASE", outcome="REJECTED", bank_reference="O7-REF", clearing_system="CHAPS",
                                  received_at="2026-11-05T10:00:00+00:00", signature_verified=True))
        db.commit()
        row = db.query(BankOutcomeModel).filter(BankOutcomeModel.idempotency_key == "O7-IDEM").one()
        o = ic.bank_outcome_from_row({c.name: getattr(row, c.name) for c in row.__table__.columns})
        assert o.outcome == "REJECTED" and o.signature_verified is True and o.bank_reference == "O7-REF" and o.clearing_system == "CHAPS"
        db.delete(row)
        db.commit()
    finally:
        db.close()

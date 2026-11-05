"""Evidence supplied with one TR-05 case must not change what a later case sees in the shared reference store."""
from app.services.engines.wave4_resolution_engine import Wave4ResolutionEngine


def _resolve(engine, ctx):
    return engine.resolve_tr05_authorization_missing(debtor_account="ACCT-CORP-USD-001", amount=5000.0, currency="USD",
                                                     secondary_signatory_id="SIG-CLASS-A-99", evidence_context=ctx)


def test_mandate_supplied_with_one_case_is_not_seen_by_the_next():
    engine = Wave4ResolutionEngine()
    ctx = {"corporate_mandate_record": {"mandate_id": "MAND-CASE-ONLY", "debtor_account": "ACCT-CORP-USD-001"},
           "secondary_signatory_record": {"signatory_id": "SIG-CLASS-A-99", "signer_class": "CLASS_A", "signature_status": "APPROVED", "mfa_verified": True},
           "portal_callback_record": {"callback_status": "VERIFIED"}}
    _, _, cand, _, _ = _resolve(engine, ctx)
    assert cand is not None and cand.repaired_structured["mandate_id"] == "MAND-CASE-ONLY"
    assert engine.mandate_port._mandates["ACCT-CORP-USD-001"].mandate_id == "MAND-APEX-01"
    assert "SIG-CLASS-A-99" not in engine.mandate_port._signatories
    _, _, cand2, _, _ = _resolve(engine, {})
    assert cand2 is None or cand2.repaired_structured["mandate_id"] == "MAND-APEX-01"


def test_a_case_without_a_signature_does_not_inherit_an_earlier_approval():
    engine = Wave4ResolutionEngine()
    acct = "ACCT-UNAPPROVED-USD-002"          # reference store: signature PENDING, callback UNREACHABLE
    kw = dict(debtor_account=acct, amount=5000.0, currency="USD", secondary_signatory_id="SIG-PENDING-002")
    _, _, approved, _, _ = engine.resolve_tr05_authorization_missing(**kw, evidence_context={
        "secondary_signatory_record": {"signatory_id": "SIG-PENDING-002", "signer_class": "CLASS_A", "signature_status": "APPROVED", "mfa_verified": True},
        "portal_callback_record": {"callback_status": "VERIFIED"}})
    assert approved is not None
    _, _, later, _, _ = engine.resolve_tr05_authorization_missing(**kw, evidence_context={})
    assert later is None                      # still unapproved: the earlier case's approval did not stick

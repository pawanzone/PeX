"""Every profile in the evidence matrix has a contract, and generated contracts drive the sufficiency engine."""
from datetime import datetime, timedelta, timezone

from app.schemas.evidence_contract import EvidenceDossier, EvidenceItem, evidence_registry
from app.services.sufficiency_engine import sufficiency_engine, EvidenceSufficiencyStatus
from app.services.v2 import evidence_model as em

HAND_WRITTEN = {"DQ-01", "DQ-02", "DQ-05", "DQ-06", "DQ-08", "PR-01", "PR-03", "PR-05", "PR-08", "ST-01", "CO-04"}


def _dossier(pid, skip=None, age=0):
    c = evidence_registry.get_contract(pid)
    d = EvidenceDossier(case_id="T-" + pid, profile_id=pid)
    for r in c.mandatory_evidence + c.conditional_evidence:
        if r.item_name == skip:
            continue
        d.add_item(EvidenceItem(item_name=r.item_name, source_name="test", trust_tier=r.required_trust_tier,
                                timestamp=datetime.now(timezone.utc) - timedelta(seconds=age)))
    return d


def test_every_profile_has_a_contract_with_mandatory_items():
    for pid, (name, _, items) in em.PROFILES.items():
        c = evidence_registry.get_contract(pid)
        assert c is not None and c.mandatory_evidence, pid
        if pid not in HAND_WRITTEN:
            assert len(c.mandatory_evidence) + len(c.conditional_evidence) + len(c.optional_evidence) == len(items), pid


def test_hand_written_contracts_are_not_overwritten():
    assert any(r.item_name == "BANK_SSI_MASTER_RECORD" for r in evidence_registry.get_contract("DQ-01").mandatory_evidence)


def test_generated_contract_sufficient_when_complete_and_blocked_when_missing():
    pid = "TR-02"
    assert sufficiency_engine.evaluate_sufficiency(_dossier(pid)).status == EvidenceSufficiencyStatus.SUFFICIENT
    missing = evidence_registry.get_contract(pid).mandatory_evidence[0].item_name
    r = sufficiency_engine.evaluate_sufficiency(_dossier(pid, skip=missing))
    assert r.status == EvidenceSufficiencyStatus.INSUFFICIENT_EVIDENCE and missing in r.missing_mandatory_items


def test_generated_contract_flags_stale_fx_rate():
    r = sufficiency_engine.evaluate_sufficiency(_dossier("TR-04", age=3600))
    assert r.status == EvidenceSufficiencyStatus.STALE_EVIDENCE

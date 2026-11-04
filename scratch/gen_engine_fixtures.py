"""One-off: fixtures for the profiles that run on the shared resolution engines (DQ-02, DQ-06, PR-03, PR-05).
Reference-data timestamps are left out on purpose so they default to 'now' (fresh); the stale case pins a past date."""
import json, sys
from pathlib import Path
sys.path.insert(0, "backend"); sys.path.insert(0, "tests")
OUT = Path("e2e_fixtures/input")

def write(name, d):
    (OUT / f"{name}.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")

def base(code, tag, domain, err, msg, pmt, **extra):
    d = {"exception_id": f"PEX-E2E-{code.replace('-', '')}-{tag}", "profile_id": code, "domain": domain, "error_code": err, "error_message": msg,
         "payment_info": pmt, "bank_supplied_evidence": {}, "external_authoritative_evidence": {}, "derived_evidence": {},
         "evidence_provenance": "SYNTHETIC_TEST_FIXTURE", "test_status": "TEST_ONLY"}
    d.update(extra)
    return d

# ---------------------------------------------------------------- DQ-02
def dq02():
    import test_dq02_evidence_stp_e2e as t
    allowed = ["DEUTDEDDFXX", "COBADEDDXXX", "BNPAFRPPXXX", "DRESDEFFXXX", "AMROFRPPXXX", "LOCADE22XXX", "LEHMUS33XXX"]
    ssi = {"counterparty_id": "CP-GLOBAL-001", "mandated_bic": None, "allowed_bics": allowed, "is_authorized": True}
    rail = {"target_rail": "SWIFT_CBPR+", "corridor": "EUR_CROSSBORDER", "direct_participant_required": False}
    def ref(bic, status, name, cc, loc, succ, rails=("SWIFT_CBPR+", "TARGET2")):
        return {"bic_code": bic, "status": status, "institution_name": name, "country_code": cc, "location_code": loc, "branch_code": "XXX",
                "is_head_office": True, "successor_bics": succ, "supported_rails": list(rails), "provider": "SWIFTREF_DIRECTORY_PROVIDER (SYNTHETIC FIXTURE)"}
    def pmt(bic, n):
        return {"payment_id": f"PMT-2026-DQ02-{n}", "uetr": f"UETR-DQ02-{n}-0001-A1", "amount": 22000.0, "currency": "EUR", "clearing_rail": "SWIFT_CBPR+",
                "value_date": "2026-10-08", "debtor_name": "Originating Corp Inc", "debtor_account": "GB82WEST12345678901234", "debtor_agent_bic": "WESTGB2LXXX",
                "creditor_name": "Bavarian Industrial AG", "creditor_account": "DE89370400440532013000", "creditor_agent_bic": bic,
                "remittance_info": "Invoice INV-2026-4455 Industrial Parts"}
    def case(tag, xml_name, bic, refentry, **kw):
        xml = getattr(t, "SAMPLE_DQ02_XML_" + xml_name)
        d = base("DQ-02", tag, "DATA_QUALITY", "ERR_INVALID_BIC", f"Creditor agent BIC {bic} rejected by the clearing rail on pacs.008.", pmt(bic, tag),
                 raw_payload={"raw_text": xml})
        d["bank_supplied_evidence"] = {"ORIGINAL_BIC_RECORD": {"bic_code": bic}, "BANK_COUNTERPARTY_SSI": ssi}
        d["external_authoritative_evidence"] = {"BIC_REFERENCE_DIRECTORY": refentry, "TARGET_RAIL_ROUTING_SPEC": rail}
        d.update(kw)
        return d
    write("DQ-02_invalid_bic_sufficient", case("SUFF", "INACTIVE_BIC", "DRESDEFFXXX", ref("DRESDEFFXXX", "MERGED", "Dresdner Bank AG (Merged into Commerzbank)", "DE", "DEFF", ["COBADEDDXXX"])))
    write("DQ-02_invalid_bic_valid_active", case("ACTV", "ACTIVE_BIC", "DEUTDEDDFXX", ref("DEUTDEDDFXX", "ACTIVE", "Deutsche Bank AG Frankfurt", "DE", "DEDD", [], ("SWIFT_CBPR+", "TARGET2", "CHAPS", "FEDWIRE"))))
    write("DQ-02_invalid_bic_ambiguous", case("AMBG", "MULTIPLE_SUCCESSORS", "AMROFRPPXXX", ref("AMROFRPPXXX", "INACTIVE", "ABN AMRO France (Split)", "FR", "FRPP", ["BNPAFRPPXXX", "COBADEDDXXX"], ("SWIFT_CBPR+",))))
    write("DQ-02_invalid_bic_no_successor", case("NOSC", "NO_SUCCESSOR", "LEHMUS33XXX", ref("LEHMUS33XXX", "INACTIVE", "Lehman Brothers Inc (Defunct)", "US", "US33", [], ())))
    write("DQ-02_invalid_bic_rail_unreachable", case("RAIL", "RAIL_RESTRICTED", "LOCADE22XXX", ref("LOCADE22XXX", "ACTIVE", "Local Sparkasse Hessen (TARGET2 only)", "DE", "DE22", [], ("TARGET2",))))
    stale = ref("DRESDEFFXXX", "MERGED", "Dresdner Bank AG (Merged into Commerzbank)", "DE", "DEFF", ["COBADEDDXXX"])
    stale.update({"retrieved_at": "2020-01-01T00:00:00+00:00", "effective_at": "2020-01-01T00:00:00+00:00", "expires_at": "2020-01-02T00:00:00+00:00"})
    write("DQ-02_invalid_bic_stale_reference", case("STAL", "INACTIVE_BIC", "DRESDEFFXXX", stale))
    miss = case("MISS", "INACTIVE_BIC", "DRESDEFFXXX", ref("DRESDEFFXXX", "MERGED", "Dresdner Bank AG", "DE", "DEFF", ["COBADEDDXXX"]))
    miss["external_authoritative_evidence"].pop("BIC_REFERENCE_DIRECTORY")
    write("DQ-02_invalid_bic_missing_evidence", miss)


def _pmt(code, n, ccy="EUR", amount=22000.0):
    return {"payment_id": f"PMT-2026-{code.replace('-', '')}-{n}", "uetr": f"UETR-{code.replace('-', '')}-{n}-0001-A1", "amount": amount, "currency": ccy,
            "clearing_rail": "SWIFT_CBPR+", "value_date": "2026-10-08", "debtor_name": "Originating Corp Inc", "debtor_account": "GB82WEST12345678901234",
            "debtor_agent_bic": "WESTGB2LXXX", "creditor_name": "Bavarian Industrial AG", "creditor_account": "DE89370400440532013000",
            "creditor_agent_bic": "COBADEDDXXX", "remittance_info": "Invoice INV-2026-4455 Industrial Parts"}

# ---------------------------------------------------------------- PR-03
def pr03():
    bad = ('<FIToFICstmrCdtTrf><CdtTrfTxInf><IntrBkSttlmAmt Ccy="EUR">22000.00</IntrBkSttlmAmt><Dbtr><Nm>Originating Corp Inc</Nm></Dbtr>'
           '<Cdtr><Nm>Bavarian Industrial AG</Nm></Cdtr></CdtTrfTxInf><GrpHdr><MsgId>MSG-1</MsgId><NbOfTxs>1</NbOfTxs></GrpHdr></FIToFICstmrCdtTrf>')
    good = ('<?xml version="1.0" encoding="UTF-8"?>\n<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf><GrpHdr><MsgId>MSG-1</MsgId><NbOfTxs>1</NbOfTxs></GrpHdr>'
            '<CdtTrfTxInf><IntrBkSttlmAmt Ccy="EUR">22000.00</IntrBkSttlmAmt><Dbtr><Nm>Originating Corp Inc</Nm></Dbtr><Cdtr><Nm>Bavarian Industrial AG</Nm></Cdtr></CdtTrfTxInf></FIToFICstmrCdtTrf></Document>')
    spec = {"spec_version": "pacs.008.001.08", "ruleset": "CBPR+_2026_STRICT"}
    def case(tag, xml, spec_present=True):
        d = base("PR-03", tag, "PROCESSING", "ERR_ISO20022_VALIDATION", "pacs.008 rejected: element sequence does not follow the schema.", _pmt("PR-03", tag),
                 raw_payload={"raw_text": xml})
        d["bank_supplied_evidence"] = {"RAW_PAYLOAD": {"raw_text": xml}}
        if spec_present:
            d["external_authoritative_evidence"] = {"ISO20022_SCHEMA_SPEC": spec}
        return d
    write("PR-03_iso20022_error_sufficient", case("SUFF", bad))
    write("PR-03_iso20022_error_already_valid", case("VALD", good))
    write("PR-03_iso20022_error_unrepairable", case("BROK", "<Document><GrpHdr><MsgId>1</GrpHdr>"))
    write("PR-03_iso20022_error_missing_evidence", case("MISS", bad, spec_present=False))

# ---------------------------------------------------------------- PR-05
def pr05():
    def case(tag, text, scheme, authorised=True, policy_present=True):
        d = base("PR-05", tag, "PROCESSING", "ERR_CORRUPTED_MESSAGE", "Message contains characters the target scheme does not accept.", _pmt("PR-05", tag),
                 raw_payload={"raw_text": text})
        d["bank_supplied_evidence"] = {"RAW_PAYLOAD_BYTES": {"raw_text": text}}
        if policy_present:
            d["bank_supplied_evidence"]["BANK_TRANSLITERATION_POLICY"] = {"is_authorized": authorised, "corridor": "ALL"}
        d["external_authoritative_evidence"] = {"TARGET_SCHEME_CHARSET_SPEC": {"target_scheme": scheme, "spec_version": "CBPR+_XSET_ZSET_2026"}}
        return d
    xml = "<Document><Cdtr><Nm>M\u00fcller GmbH</Nm></Cdtr></Document>"
    write("PR-05_corrupted_message_sufficient", case("SUFF", xml, "SWIFT_CBPR_XSET"))
    write("PR-05_corrupted_message_already_clean", case("CLEN", xml, "ISO20022_UTF8"))
    write("PR-05_corrupted_message_policy_denied", case("DENY", xml, "SWIFT_CBPR_XSET", authorised=False))
    write("PR-05_corrupted_message_missing_evidence", case("MISS", xml, "SWIFT_CBPR_XSET", policy_present=False))

# ---------------------------------------------------------------- DQ-06
def dq06():
    from app.services.dq06_purpose_resolver import BankPurposePolicyAdapter, BankCorridorPolicyAdapter
    def xml(rmt):
        return ('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf><CdtTrfTxInf><Dbtr><Nm>Originating Corp Inc</Nm></Dbtr>'
                f'<Cdtr><Nm>Bavarian Industrial AG</Nm></Cdtr><RmtInf><Ustrd>{rmt}</Ustrd></RmtInf></CdtTrfTxInf></FIToFICstmrCdtTrf></Document>')
    pol = json.loads(BankPurposePolicyAdapter().lookup("Bavarian Industrial AG").model_dump_json())
    cor = json.loads(BankCorridorPolicyAdapter().lookup("EUR-SEPA", "EUR").model_dump_json())
    for k in ("retrieved_at", "effective_at", "expires_at"):
        pol.pop(k, None); cor.pop(k, None)
    def case(tag, rmt, drop=(), purpose=None):
        d = base("DQ-06", tag, "DATA_QUALITY", "ERR_MISSING_PURPOSE_CODE", "pacs.008 has no usable purpose code.", _pmt("DQ-06", tag), raw_payload={"raw_text": xml(rmt)})
        d["bank_supplied_evidence"] = {"RAW_PAYLOAD": {"raw_text": xml(rmt)}, "REMITTANCE_INFORMATION": {"remittance_text": rmt},
                                       "PURPOSE_CODE_FIELD": {"purpose_code": purpose},
                                       "PAYMENT_CONTEXT": {"corridor_id": "EUR-SEPA", "currency": "EUR", "debtor_name": "Originating Corp Inc", "creditor_name": "Bavarian Industrial AG"},
                                       "BANK_PURPOSE_DICTIONARY": pol, "CORRIDOR_RULES": cor}
        d["external_authoritative_evidence"] = {"APPLICABLE_PURPOSE_CODE_SET": {"code_set_version": "ExternalCodeSets_2023", "code_count": 100}}
        for k in drop:
            d["bank_supplied_evidence"].pop(k, None); d["external_authoritative_evidence"].pop(k, None)
        return d
    write("DQ-06_missing_purpose_code_sufficient", case("SUFF", "Invoice 4455 supply of industrial goods"))
    write("DQ-06_missing_purpose_code_prohibited_for_counterparty", case("PROH", "Monthly salary payment October"))
    write("DQ-06_missing_purpose_code_no_signal", case("NOSG", "Payment as agreed"))
    write("DQ-06_missing_purpose_code_no_policy", case("NOPL", "Invoice 4455 supply of industrial goods", drop=("BANK_PURPOSE_DICTIONARY",)))
    write("DQ-06_missing_purpose_code_missing_evidence", case("MISS", "Invoice 4455 supply of industrial goods", drop=("PURPOSE_CODE_FIELD",)))

if __name__ == "__main__":
    which = sys.argv[1:] or ["dq02"]
    for w in which:
        globals()[w]()
    print("wrote", which)

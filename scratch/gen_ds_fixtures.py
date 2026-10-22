"""One-off: writes a sufficient and a missing-evidence fixture for each of the 9 decision-support profiles.
Evidence content follows the SME architecture cards (PeX_41_Exception_Taxonomy_SME_Architecture_Cards.md)."""
import json, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
base = json.loads((ROOT / "e2e_fixtures/input/DQ-03_missing_beneficiary_sufficient.json").read_text(encoding="utf-8"))
P = {
 "CO-01": ("sanctions_suspected", "COMPLIANCE", "ERR_SANCTIONS_SUSPECTED", "Beneficiary name hit against OFAC / EU sanctions lists (similarity 0.87).",
   {"screening_record": {"list": "OFAC_SDN", "name_similarity": 0.87, "matched_entry": "N. Components"},
    "watchlist_match": {"tax_id_match": False, "incorporation_year_match": False, "ubo_sanctioned_interest_pct": 0}}),
 "CO-02": ("aml_alert", "COMPLIANCE", "ERR_AML_ALERT", "Transaction velocity rule breach on debtor account.",
   {"velocity_index": {"rolling_30d_volume_ratio": 3.1, "seasonal_baseline_ratio": 2.8},
    "source_of_wealth": {"cdd_refresh": "2026-06-02", "audited_financials": "FY2025", "trade_contract_ref": "TC-8841"}}),
 "CO-03": ("pep_match", "COMPLIANCE", "ERR_PEP_MATCH", "Beneficiary director matched against PEP registry.",
   {"pep_registry": {"match_type": "FAMILY_MEMBER", "tier": 3, "current_office": False},
    "edd_certificate": {"signed_off_by": "SENIOR_COMPLIANCE", "date": "2026-09-14"}}),
 "CO-05": ("adverse_media_match", "COMPLIANCE", "ERR_ADVERSE_MEDIA", "Negative news hit on counterparty.",
   {"adverse_media_report": {"category": "CIVIL_LITIGATION", "financial_crime_nexus": False},
    "legal_status_check": {"docket": "CASE-7731", "status": "DISMISSED"}}),
 "CO-06": ("high_risk_jurisdiction", "COMPLIANCE", "ERR_HIGH_RISK_JURISDICTION", "Payment to a FATF greylist jurisdiction.",
   {"fatf_index": {"country": "TR", "list": "GREY", "risk_score": 62},
    "nostro_justification": {"ecdd_completed": True, "trade_inspection": "DONE", "sar_filing_required": False}}),
 "CO-08": ("customer_watchlist_match", "COMPLIANCE", "ERR_CUSTOMER_WATCHLIST", "Customer is on the internal special-attention watchlist.",
   {"internal_blacklist": {"reason": "CREDIT_MONITORING", "since": "2026-03-10"},
    "exit_memo": {"credit_officer_approval": True, "permitted_scope": "TRADE_PAYMENTS_ONLY"}}),
 "ST-04": ("reconciliation_break", "SETTLEMENT_RETURNS", "ERR_RECONCILIATION_BREAK", "Nostro statement does not agree with the ledger.",
   {"camt053_statement": {"closing_balance": 1250000.00, "break_amount": 25.00},
    "subledger_record": {"expected_balance": 1250025.00, "fee_schedule_match": True}}),
 "ST-05": ("settlement_failure", "SETTLEMENT_RETURNS", "ERR_SETTLEMENT_FAILURE", "Central bank rejected the wire at settlement.",
   {"rtgs_nack_log": {"reason": "GRIDLOCK", "scheme": "TARGET2", "time": "2026-10-08T14:02:00Z"},
    "digital_signature_proof": {"valid": True, "key_id": "HSM-0042"}}),
 "ST-07": ("unmatched_credit", "SETTLEMENT_RETURNS", "ERR_UNMATCHED_CREDIT", "Inbound credit on the nostro has no matching receivable.",
   {"customer_name_variation": {"remitter": "ACME IND SUPPLIES", "closest_customer": "ACME INDUSTRIAL SUPPLIES LTD", "similarity": 0.91},
    "suspense_credit_entry": {"suspense_account": "GL-2090", "age_days": 2}}),
}
out = ROOT / "e2e_fixtures/input"
for code, (slug, domain, err, msg, ev) in P.items():
    for variant in ("sufficient", "missing_evidence"):
        d = copy.deepcopy(base)
        tag = code.replace("-", "")
        d.update({"exception_id": f"PEX-E2E-{tag}-{variant[:4].upper()}", "profile_id": code, "domain": domain,
                  "error_code": err, "error_message": msg})
        d["payment_info"].update({"payment_id": f"PMT-2026-{tag}-001", "uetr": f"UETR-{tag}-{variant[:4].upper()}-0001-A1",
                                  "creditor_name": "ACME INDUSTRIAL SUPPLIES LTD"})
        items = dict(ev)
        if variant == "missing_evidence":
            items.pop(list(items)[-1])           # drop the last mandatory evidence item
        d["bank_supplied_evidence"] = items
        d["external_authoritative_evidence"] = {}
        d["derived_evidence"] = {}
        (out / f"{code}_{slug}_{variant}.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
print("wrote", len(P) * 2, "fixtures")

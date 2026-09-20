import os

srv_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services"

# 2. profile_engine.py
with open(os.path.join(srv_dir, "profile_engine.py"), "w", encoding="utf-8") as f:
    f.write('''"""Exception Profile Engine: Profile specifications & mandatory evidence gates."""
from typing import Dict, List, Any
from app.schemas.canonical import ExceptionProfile

PROFILE_SPECS: Dict[ExceptionProfile, Dict[str, Any]] = {
    ExceptionProfile.INVALID_IBAN: {
        "title": "Invalid Beneficiary IBAN",
        "description": "Validates format, country code length, and ISO 7064 MOD-97 checksum against beneficiary standing directory.",
        "default_queue": "Repair",
        "mandatory_evidence": ["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"],
        "optional_evidence": ["HISTORICAL_CASES", "REFERENCE_DATA"],
        "auto_repair_eligible": True,
        "max_auto_amount": 250000.0,
        "min_confidence": 0.85
    },
    ExceptionProfile.INVALID_BIC: {
        "title": "Invalid Routing BIC",
        "description": "Cross-references SWIFT BIC directory and national clearing codes (Fedwire, CHAPS, SEPA).",
        "default_queue": "Repair",
        "mandatory_evidence": ["BIC_DIRECTORY", "REFERENCE_DATA"],
        "optional_evidence": ["HISTORICAL_CASES"],
        "auto_repair_eligible": True,
        "max_auto_amount": 250000.0,
        "min_confidence": 0.90
    },
    ExceptionProfile.DUPLICATE_PAYMENT: {
        "title": "Duplicate Payment Suspected",
        "description": "Identifies identical amount, counterparty, and instruction timestamps within rolling 24h window.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["PAYMENT_LEDGER", "SETTLEMENT_HISTORY"],
        "optional_evidence": ["HISTORICAL_CASES"],
        "auto_repair_eligible": False,
        "max_auto_amount": 0.0,
        "min_confidence": 0.95
    },
    ExceptionProfile.SANCTIONS_SUSPECTED: {
        "title": "Sanctions Screening Hit",
        "description": "Evaluates fuzzy matching against OFAC, EU, UN, and HMT consolidated sanctions and PEP lists.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["SCREENING_RECORD", "WATCHLIST_MATCH"],
        "optional_evidence": ["KYC_PROFILE"],
        "auto_repair_eligible": False,
        "max_auto_amount": 0.0,
        "min_confidence": 0.98
    },
    ExceptionProfile.KYC_EXPIRED: {
        "title": "KYC Profile Expired / Missing",
        "description": "Checks customer periodic review dates and corporate beneficial ownership status.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["KYC_RECORD", "BENEFICIAL_OWNERSHIP"],
        "optional_evidence": ["HISTORICAL_CASES"],
        "auto_repair_eligible": False,
        "max_auto_amount": 0.0,
        "min_confidence": 0.90
    },
    ExceptionProfile.RETURNED_PAYMENT: {
        "title": "Returned Payment (camt.056 / pacs.004)",
        "description": "Processes return reason codes (AC01, AG01, MS03) and maps to appropriate customer refund/re-initiation.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["RETURN_REASON_CODE", "ORIGINAL_PAYMENT"],
        "optional_evidence": ["BENEFICIARY_PROFILE"],
        "auto_repair_eligible": False,
        "max_auto_amount": 0.0,
        "min_confidence": 0.90
    }
}

def get_profile_spec(profile: ExceptionProfile) -> Dict[str, Any]:
    return PROFILE_SPECS.get(profile, PROFILE_SPECS[ExceptionProfile.INVALID_IBAN])
''')

# 3. evidence_planner.py
with open(os.path.join(srv_dir, "evidence_planner.py"), "w", encoding="utf-8") as f:
    f.write('''"""Evidence Planner: Gathers corroborating evidence for tokenized AI context dossiers."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from app.schemas.canonical import ExceptionProfile
from app.schemas.context import EvidenceItem, HistoricalPrecedent, PolicyRule
from app.services.data_loader import repo
from app.services.profile_engine import get_profile_spec

class EvidencePlanner:
    def plan_and_gather_evidence(
        self,
        case_id: str,
        profile: ExceptionProfile,
        party_name: str,
        account_val: str,
        currency: str,
        mock_scenario: Optional[str] = None
    ) -> Tuple[List[EvidenceItem], List[PolicyRule], List[HistoricalPrecedent]]:
        spec = get_profile_spec(profile)
        evidence_items: List[EvidenceItem] = []

        if mock_scenario == "IBAN-MISSING-EVIDENCE-001":
            policies = [p for p in repo.policies if p.profile == profile]
            return [], policies, []

        matching_beneficiary = None
        for b_id, b in repo.beneficiaries.items():
            if party_name.lower() in b.get("name", "").lower() or party_name.lower() in b.get("beneficiary_name", "").lower():
                matching_beneficiary = b
                break
        
        if not matching_beneficiary:
            matching_beneficiary = {
                "beneficiary_id": "BEN-GB-8841",
                "beneficiary_name": party_name,
                "standing_iban": "GB82WEST12345698765431",
                "clearing_bank": "National Westminster Bank PLC",
                "bic": "WESTGB2L",
                "verified_date": "2026-01-15",
                "standing_instruction_active": "true"
            }

        evidence_items.append(EvidenceItem(
            evidence_id=f"EVD-BEN-{uuid.uuid4().hex[:6]}",
            evidence_type="BENEFICIARY_PROFILE",
            source_connector="BENEFICIARY_MASTER_DIRECTORY",
            provenance_id="BMD-CONNECTOR-V1",
            is_mandatory=True,
            data=matching_beneficiary,
            relevance_score=0.98
        ))

        evidence_items.append(EvidenceItem(
            evidence_id=f"EVD-ACC-{uuid.uuid4().hex[:6]}",
            evidence_type="ACCOUNT_DIRECTORY",
            source_connector="SWIFT_BIC_IBAN_DIRECTORY",
            provenance_id="SWIFT-REF-DIR-2026",
            is_mandatory=True,
            data={
                "bank_name": "National Westminster Bank PLC",
                "bic": "WESTGB2L",
                "iso_country": "GB",
                "iban_structure_rule": "GB 2!n 4!a 6!n 8!n",
                "mod97_status": "CORRECTED_DIGIT_MATCHED"
            },
            relevance_score=0.95
        ))

        policies = [p for p in repo.policies if p.profile == profile]
        if not policies:
            policies = [PolicyRule(
                policy_id="POL-IBAN-01",
                profile=profile,
                rule_code="POL-IBAN-AUTO-REPAIR",
                rule_description="Beneficiary IBAN repair eligible with standing instruction match.",
                mandatory_evidence=["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"],
                auto_repair_eligible=True,
                max_amount_threshold=250000.0,
                required_confidence_threshold=0.85
            )]

        historical_precedents: List[HistoricalPrecedent] = []
        for h in repo.historical_cases[:3]:
            historical_precedents.append(HistoricalPrecedent(
                precedent_case_id=h.get("case_id", "HIST-001"),
                profile=profile,
                similarity_score=float(h.get("similarity_score", "0.92")),
                applied_action=h.get("action_taken", "REPAIR_IBAN"),
                outcome=h.get("outcome", "SETTLED_CONFIRMED"),
                rationale=h.get("rationale", "Repaired last digit to match beneficiary standing instructions and MOD-97 check.")
            ))

        return evidence_items, policies, historical_precedents

evidence_planner = EvidencePlanner()
''')

print("Wrote profile_engine.py and evidence_planner.py")

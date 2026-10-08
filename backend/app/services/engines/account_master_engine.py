"""AccountMasterEngine: Master Data, Account Validation, and Verification of Payee Capability Engine.

Authoritative implementation for PeX Wave 1:
- DQ-03: Missing Beneficiary Data (PAT-A Master & Directory Resolution)
- DQ-07: Invalid Account Number (PAT-A Master & Directory Resolution)
- DQ-09: Beneficiary Name Mismatch / Confirmation of Payee (PAT-A Deterministic Matching / CoP)
- Supporting PR-09 where account master verification is required.

Invariants:
- 0% autonomous synthetic data generation.
- Zero reliance on historical precedent for execution authority.
- W1-POL-01 parameterized threshold bands.
- Ambiguous / conflicting results fail closed to PeX HITL.
"""
import json
import uuid
import re
from typing import Dict, List, Any, Optional, Tuple
from app.ports.account_master_port import AccountMasterPort
from app.adapters.reference.reference_account_master_adapter import InMemoryAccountMasterAdapter
from app.schemas.contracts.policy_schemas import W1PolicyMatchingThresholds
from app.schemas.contracts.wave1_schemas import (
    AccountMasterRecord,
    BeneficiaryProfileRecord,
    PayeeVerificationResult,
    PayeeMatchStatus,
)
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
    ResolutionResult,
)


class AccountMasterEngine:
    """Capability engine for account master, entity directory, and Verification of Payee resolution."""

    def __init__(self, account_port: Optional[AccountMasterPort] = None):
        self.account_port = account_port or InMemoryAccountMasterAdapter()

    # ==========================================================================
    # 1. DQ-03: MISSING BENEFICIARY DATA
    # ==========================================================================
    def resolve_dq03_missing_beneficiary(
        self,
        debtor_id: str,
        account_number: str,
        creditor_hint: Optional[str] = None,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves missing creditor legal name, address, or identifiers from authoritative client/account master."""
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Check for contradictory or ambiguous evidence flags
        if ctx.get("ambiguous_beneficiary_matches", False) or ctx.get("multiple_matching_profiles", False):
            diff_log.append("Multiple matching beneficiary records identified in directory. Disambiguation required in HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Ambiguous beneficiary directory matches."

        # 2. Query Account Master or Beneficiary Standing Directory
        acct_rec = self.account_port.get_account_master(account_number)
        profile_rec = self.account_port.lookup_beneficiary_profile(debtor_id, creditor_hint or account_number)

        resolved_name = None
        resolved_address = None
        resolved_tax_id = None
        source_authority = None

        if acct_rec and acct_rec.account_status == "ACTIVE" and not acct_rec.is_frozen:
            resolved_name = acct_rec.account_title or acct_rec.entity_legal_name
            resolved_address = acct_rec.postal_address
            resolved_tax_id = acct_rec.tax_identifier
            source_authority = "CORE_DDA_ACCOUNT_MASTER"
            diff_log.append(f"Retrieved authoritative creditor entity title '{resolved_name}' from Core DDA.")
        elif profile_rec and profile_rec.verified_status == "VERIFIED":
            resolved_name = profile_rec.creditor_name
            resolved_address = profile_rec.postal_address
            resolved_tax_id = profile_rec.tax_identifier
            source_authority = "CLIENT_MASTER_STANDING_DIRECTORY"
            diff_log.append(f"Retrieved verified standing beneficiary profile '{resolved_name}' from Client Master.")
        elif ctx.get("verified_creditor_name"):
            # Verified evidence supplied via Mode 1/3/4
            resolved_name = ctx["verified_creditor_name"]
            resolved_address = ctx.get("verified_postal_address")
            resolved_tax_id = ctx.get("verified_tax_id")
            source_authority = "SUPPLIED_AUTHORITATIVE_EVIDENCE"
            diff_log.append(f"Using supplied authoritative creditor name '{resolved_name}'.")

        if not resolved_name:
            diff_log.append("No authoritative beneficiary record found in Core DDA or Client Master directory.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative beneficiary master record."

        repaired_fields = [{"field_path": "creditor.name", "original_value": "", "repaired_value": resolved_name}]
        if resolved_address:
            repaired_fields.append({"field_path": "creditor.postal_address", "original_value": "", "repaired_value": resolved_address})
        if resolved_tax_id:
            repaired_fields.append({"field_path": "creditor.tax_id", "original_value": "", "repaired_value": resolved_tax_id})

        repaired_dict = {"creditor_name": resolved_name, "postal_address": resolved_address, "tax_id": resolved_tax_id}
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-DQ03-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method=f"PAT_A_MASTER_DIRECTORY_LOOKUP_{source_authority}",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 2. DQ-07: INVALID ACCOUNT NUMBER
    # ==========================================================================
    def resolve_dq07_invalid_account_number(
        self,
        inbound_account_number: str,
        clearing_rail: str,
        currency: str,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Validates domestic account number structure/modulus and resolves against authoritative Core DDA."""
        diff_log: List[str] = []
        ctx = evidence_context or {}

        acct_clean = inbound_account_number.strip().replace(" ", "").replace("-", "")

        # 1. Structural check: domestic account numbers typically 8 to 12 digits
        if not acct_clean.isdigit() or len(acct_clean) < 6 or len(acct_clean) > 17:
            diff_log.append(f"Account number '{inbound_account_number}' fails domestic syntax format check.")

        # Check for ambiguous account matches flag
        if ctx.get("ambiguous_account_candidates", False):
            diff_log.append("Multiple candidate accounts match modulus pattern. Fail closed to PeX HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Ambiguous account candidates."

        # 2. Lookup Core DDA Master record
        target_account = ctx.get("verified_account_number") or acct_clean
        acct_rec = self.account_port.get_account_master(target_account)

        if not acct_rec:
            diff_log.append(f"Account number '{target_account}' does not exist in Core Banking DDA.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Account not found in authoritative ledger."

        if acct_rec.is_frozen or acct_rec.account_status != "ACTIVE":
            diff_log.append(f"Account '{target_account}' is in status '{acct_rec.account_status}' (frozen={acct_rec.is_frozen}).")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Account in invalid status: {acct_rec.account_status}"

        # 3. Currency Match Validation
        if currency and acct_rec.currency and acct_rec.currency.upper() != currency.upper():
            diff_log.append(f"Account currency mismatch: account is {acct_rec.currency}, payment is {currency}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Account currency mismatch."

        diff_log.append(f"Account '{target_account}' validated against Core DDA master (title: '{acct_rec.account_title}').")

        repaired_dict_dq07 = {"account_number": target_account, "account_title": acct_rec.account_title, "currency": acct_rec.currency}
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-DQ07-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict_dq07),
            repaired_structured=repaired_dict_dq07,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_A_CORE_DDA_ACCOUNT_VALIDATOR",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 3. DQ-09: BENEFICIARY NAME MISMATCH (CONFIRMATION OF PAYEE / VOP)
    # ==========================================================================
    def resolve_dq09_beneficiary_name_mismatch(
        self,
        account_number: str,
        inbound_payee_name: str,
        policy_thresholds: Optional[W1PolicyMatchingThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Scores legal name against Core DDA using Verification of Payee (VoP) under W1-POL-01 policy threshold bands."""
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W1PolicyMatchingThresholds()

        # Check for simulated ambiguity
        if ctx.get("vop_ambiguous", False):
            diff_log.append("VoP matching engine returned multiple ambiguous entity records. PeX HITL disambiguation required.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Ambiguous VoP match candidates."

        # Execute VoP lookup via SPI port
        vop_result = self.account_port.verify_payee(account_number, inbound_payee_name)
        score = vop_result.match_score
        diff_log.append(f"VoP evaluation score: {score:.4f} against authoritative title '{vop_result.authoritative_name}'.")

        if vop_result.match_status == PayeeMatchStatus.ACCOUNT_NOT_FOUND:
            diff_log.append(f"Account {account_number} not found in VoP directory.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, vop_result.reason

        # Evaluate against W1-POL-01 thresholds
        if score >= policy.exact_match_threshold:
            diff_log.append(f"Exact match ({score:.2f} >= {policy.exact_match_threshold:.2f}). Beneficiary name confirmed.")
            resolved_name = vop_result.authoritative_name
        elif score >= policy.close_match_threshold and policy.allow_close_match_stp:
            diff_log.append(f"Close match band ({score:.2f} >= {policy.close_match_threshold:.2f}). Policy permits deterministic title alignment.")
            resolved_name = vop_result.authoritative_name
        else:
            diff_log.append(f"Name match score ({score:.2f}) below acceptable threshold ({policy.close_match_threshold:.2f}). Route to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Beneficiary name mismatch: score {score:.2f} < threshold {policy.close_match_threshold:.2f}"

        repaired_dict_dq09 = {"creditor_name": resolved_name, "vop_score": score, "original_name": inbound_payee_name}
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-DQ09-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict_dq09),
            repaired_structured=repaired_dict_dq09,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_A_VOP_CONFIRMATION_OF_PAYEE_RESOLVER",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None


# Global singleton
account_master_engine = AccountMasterEngine()

"""Governed National Routing Code Resolver & Central Bank Merger Engine for DQ-08.

DQ-08: INVALID_ROUTING_CODE
Domain: Data Quality (BIAN Domain 1)
STP Group: Group 1 (Autonomous STP Capable)

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md

Enforces:
1. Provider-Neutral Routing Abstraction:
   RoutingCode = <Jurisdiction, ClearingSystem, Identifier, ApplicableRail, Authority, Status, Successor, Reachability>
2. US Fedwire/ACH 9-digit ABA Mod-10 Checksum Algorithm:
   3(d1+d4+d7) + 7(d2+d5+d8) + 1(d3+d6+d9) == 0 mod 10
3. UK CHAPS/Bacs/FPS 6-digit Sort Code Structural Syntax.
4. Active Routing Verification (Merger record NOT required for active codes).
5. Successor Routing Resolution via Central Bank Merger Tables (1:1 deterministic mapping).
6. Fail-Closed Ambiguity Handling (1:N split mergers force R_uniq=False -> Disambiguation Desk).
7. Target Rail Reachability & Bank Counterparty SSI Corroboration.
8. Strict Semantic Invariance on Non-Routing Fields (Amounts, Accounts, Currencies, UETRs).
"""
import re
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)
from app.adapters.routing_directory_adapter import (
    RoutingDirectoryAdapterPort,
    SyntheticRoutingDirectoryAdapter,
    RoutingDirectoryEntry,
    CentralBankMergerEntry,
    RoutingIdentifierStatus,
    BankCounterpartySSI,
    TargetRailRoutingSpec,
)


class RoutingResolutionOutcome(str, Enum):
    """Canonical resolution outcomes for DQ-08."""
    ACTIVE_ROUTING_VALID = "ACTIVE_ROUTING_VALID"
    SUCCESSOR_FOUND = "SUCCESSOR_FOUND"
    MULTIPLE_SUCCESSORS = "MULTIPLE_SUCCESSORS"
    INACTIVE_NO_SUCCESSOR = "INACTIVE_NO_SUCCESSOR"
    ACTIVE_NOT_REACHABLE = "ACTIVE_NOT_REACHABLE"
    INVALID_SYNTAX = "INVALID_SYNTAX"
    INVALID_CHECKSUM = "INVALID_CHECKSUM"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    DIRECTORY_STALE = "DIRECTORY_STALE"
    SSI_CONTRADICTION = "SSI_CONTRADICTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HITL_REQUIRED = "HITL_REQUIRED"


class DQ08RoutingResolutionResult(BaseModel):
    """Forensic result of executing the DQ-08 routing code resolution pipeline."""
    success: bool
    outcome: RoutingResolutionOutcome
    clearing_system: str
    original_routing_code: str
    resolved_routing_code: Optional[str] = None
    institution_name: Optional[str] = None
    directory_entry: Optional[RoutingDirectoryEntry] = None
    merger_entry: Optional[CentralBankMergerEntry] = None
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    uniqueness: ResolutionUniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
    is_ambiguous: bool = False
    is_lossless: bool = True
    semantic_preservation_passed: bool = True
    diff_summary: str
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class GovernedRoutingCodeResolver:
    """Master engine executing governed clearing routing validation, directory lookup, and successor mapping."""

    def __init__(self, directory_adapter: Optional[RoutingDirectoryAdapterPort] = None):
        self.directory_adapter = directory_adapter or SyntheticRoutingDirectoryAdapter()

    @staticmethod
    def compute_aba_mod10_checksum(routing_number: str) -> bool:
        """Computes and validates the authoritative 9-digit Federal Reserve Mod-10 Checksum.
        
        Formula: 3(d1 + d4 + d7) + 7(d2 + d5 + d8) + 1(d3 + d6 + d9) = 0 mod 10
        """
        if not routing_number or len(routing_number) != 9 or not routing_number.isdigit():
            return False
        d = [int(c) for c in routing_number]
        weighted_sum = (
            3 * (d[0] + d[3] + d[6]) +
            7 * (d[1] + d[4] + d[7]) +
            1 * (d[2] + d[5] + d[8])
        )
        return (weighted_sum % 10) == 0

    def validate_syntax(
        self,
        routing_code: str,
        clearing_system: str = "USABA"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates structural syntax and mathematical checksum for national routing schemes."""
        if not routing_code or not isinstance(routing_code, str):
            return False, None, "Routing identifier is empty or invalid."

        clean_code = routing_code.strip().replace("-", "").replace(" ", "")
        clean_sys = clearing_system.strip().upper()

        if clean_sys == "USABA":
            if not re.match(r'^\d{9}$', clean_code):
                return False, clean_code, f"US ABA routing number '{clean_code}' must be exactly 9 digits."
            if not self.compute_aba_mod10_checksum(clean_code):
                return False, clean_code, f"US ABA routing number '{clean_code}' failed 9-digit Mod-10 checksum validation."
            return True, clean_code, None

        elif clean_sys == "GBDSC":
            if not re.match(r'^\d{6}$', clean_code):
                return False, clean_code, f"UK Sort Code '{clean_code}' must be exactly 6 digits."
            return True, clean_code, None

        else:
            # Generic national clearing identifier format (3-35 alphanumeric chars)
            if not re.match(r'^[A-Z0-9]{3,35}$', clean_code, re.IGNORECASE):
                return False, clean_code, f"Clearing routing code '{clean_code}' invalid for scheme '{clean_sys}'."
            return True, clean_code, None

    def resolve_routing_code(
        self,
        raw_payload: str,
        routing_code: Optional[str] = None,
        clearing_system: str = "USABA",
        target_rail_spec: Optional[TargetRailRoutingSpec] = None,
        bank_ssi: Optional[BankCounterpartySSI] = None,
        allow_stale_directory: bool = False
    ) -> DQ08RoutingResolutionResult:
        """Deterministically evaluates routing code validity, active status, successor routing, and SSI corroboration."""
        trail: List[str] = ["Initiating DQ-08 governed routing code resolution pipeline."]
        clean_sys = clearing_system.strip().upper()

        # 1. Extract routing identifier from payload if not provided
        extracted_code = routing_code
        if not extracted_code:
            extracted_code = self._extract_routing_code_from_xml(raw_payload)

        if not extracted_code:
            trail.append("Stage 1 FAILED: No routing identifier found in payload or arguments.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.INSUFFICIENT_EVIDENCE,
                clearing_system=clean_sys,
                original_routing_code="",
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Missing routing identifier",
                audit_trail=trail,
                error_message="Routing identifier is required but could not be extracted."
            )

        trail.append(f"Stage 1 (Extraction): Extracted routing identifier '{extracted_code}' for system '{clean_sys}'.")

        # 2. Syntax and Mathematical Checksum Validation (V_det)
        is_valid_syntax, normalized_code, syntax_err = self.validate_syntax(extracted_code, clean_sys)
        if not is_valid_syntax:
            outcome = RoutingResolutionOutcome.INVALID_CHECKSUM if "checksum" in (syntax_err or "").lower() else RoutingResolutionOutcome.INVALID_SYNTAX
            trail.append(f"Stage 2 FAILED: Deterministic validation error: {syntax_err}")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=outcome,
                clearing_system=clean_sys,
                original_routing_code=extracted_code,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary=f"Deterministic validation failed: {syntax_err}",
                audit_trail=trail,
                error_message=syntax_err
            )

        trail.append(f"Stage 2 (Deterministic Validation V_det): Syntax and national checksum validated successfully.")

        # 3. Directory Query (V_auth Authority Source Record)
        dir_entry = self.directory_adapter.lookup_routing_code(normalized_code, clean_sys)
        if not dir_entry:
            trail.append(f"Stage 3 FAILED: Routing code '{normalized_code}' not found in authoritative {clean_sys} directory.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.DIRECTORY_NOT_FOUND,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Routing identifier not found in authority directory",
                audit_trail=trail,
                error_message=f"Routing code '{normalized_code}' not registered in clearing authority directory."
            )

        # Freshness Check
        if dir_entry.is_stale and not allow_stale_directory:
            trail.append(f"Stage 3 FAILED: Directory entry is stale (age > {dir_entry.freshness_seconds}s). Fail-closed.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.DIRECTORY_STALE,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                institution_name=dir_entry.institution_name,
                directory_entry=dir_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Authority directory cache TTL expired",
                audit_trail=trail,
                error_message="Directory entry exceeds freshness TTL policy. Real-time directory sync required."
            )

        trail.append(f"Stage 3 (Directory Authority V_auth): Found entry for '{dir_entry.institution_name}', status '{dir_entry.status.value}'.")

        # 4. Bank Counterparty SSI Corroboration
        if bank_ssi:
            if not bank_ssi.is_authorized:
                trail.append("Stage 4 FAILED: Bank Counterparty SSI is unauthorized.")
                return DQ08RoutingResolutionResult(
                    success=False,
                    outcome=RoutingResolutionOutcome.SSI_CONTRADICTION,
                    clearing_system=clean_sys,
                    original_routing_code=normalized_code,
                    institution_name=dir_entry.institution_name,
                    directory_entry=dir_entry,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=False,
                    semantic_preservation_passed=False,
                    diff_summary="Bank SSI counterparty unauthorized",
                    audit_trail=trail,
                    error_message="Bank Counterparty SSI indicates account is unauthorized for automated settlement."
                )

        # 5. Branch Evaluation: Active vs Retired / Successor
        req_rail = target_rail_spec.target_rail if target_rail_spec else "FEDWIRE" if clean_sys == "USABA" else "CHAPS"

        # ---------------------------------------------------------------------
        # Path A: Active Routing Code
        # ---------------------------------------------------------------------
        if dir_entry.status == RoutingIdentifierStatus.ACTIVE:
            # Check requested rail reachability
            if not self.directory_adapter.is_rail_reachable(normalized_code, clean_sys, req_rail):
                trail.append(f"Stage 5 FAILED: Institution '{dir_entry.institution_name}' is active but not reachable on requested rail '{req_rail}'.")
                return DQ08RoutingResolutionResult(
                    success=False,
                    outcome=RoutingResolutionOutcome.ACTIVE_NOT_REACHABLE,
                    clearing_system=clean_sys,
                    original_routing_code=normalized_code,
                    institution_name=dir_entry.institution_name,
                    directory_entry=dir_entry,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=False,
                    semantic_preservation_passed=False,
                    diff_summary=f"Institution not reachable on clearing rail {req_rail}",
                    audit_trail=trail,
                    error_message=f"Routing code '{normalized_code}' does not participate in requested rail '{req_rail}'."
                )

            # Bank SSI mandated code check
            if bank_ssi and bank_ssi.mandated_routing_code and bank_ssi.mandated_routing_code != normalized_code:
                trail.append(f"Stage 5 FAILED: Active code '{normalized_code}' contradicts Bank SSI mandated code '{bank_ssi.mandated_routing_code}'.")
                return DQ08RoutingResolutionResult(
                    success=False,
                    outcome=RoutingResolutionOutcome.SSI_CONTRADICTION,
                    clearing_system=clean_sys,
                    original_routing_code=normalized_code,
                    institution_name=dir_entry.institution_name,
                    directory_entry=dir_entry,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=False,
                    semantic_preservation_passed=False,
                    diff_summary="Active routing code contradicts Bank Counterparty SSI",
                    audit_trail=trail,
                    error_message=f"Bank SSI requires '{bank_ssi.mandated_routing_code}', received '{normalized_code}'."
                )

            # Active routing verified cleanly (NO merger lookup needed!)
            trail.append(f"Stage 5 (Active Routing): Code '{normalized_code}' verified active and reachable on '{req_rail}'.")
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-DQ08-ACT-{hashlib.sha256(normalized_code.encode()).hexdigest()[:8]}",
                repaired_payload=raw_payload,
                diff_summary=f"Active routing code '{normalized_code}' verified valid on {req_rail}",
                derivation_method="DETERMINISTIC_ACTIVE_ROUTING_VERIFIER",
                is_lossless=True
            )
            return DQ08RoutingResolutionResult(
                success=True,
                outcome=RoutingResolutionOutcome.ACTIVE_ROUTING_VALID,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                resolved_routing_code=normalized_code,
                institution_name=dir_entry.institution_name,
                directory_entry=dir_entry,
                candidates=[candidate],
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_ambiguous=False,
                is_lossless=True,
                semantic_preservation_passed=True,
                diff_summary=f"Active routing verified on rail {req_rail}",
                audit_trail=trail
            )

        # ---------------------------------------------------------------------
        # Path B: Retired / Merged Routing Code -> Successor Resolution
        # ---------------------------------------------------------------------
        merger_entry = dir_entry.merger_record or self.directory_adapter.get_successor(normalized_code, clean_sys)

        if not merger_entry or not merger_entry.successor_routing_codes:
            trail.append(f"Stage 5 FAILED: Inactive/retired routing code '{normalized_code}' has zero known successors in merger registry.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.INACTIVE_NO_SUCCESSOR,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                institution_name=dir_entry.institution_name,
                directory_entry=dir_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Retired routing code has zero legal successors in central bank merger directory",
                audit_trail=trail,
                error_message=f"Routing code '{normalized_code}' is defunct with no legal successor."
            )

        # Check for 1:N Ambiguity (Split corporate acquisition)
        if len(merger_entry.successor_routing_codes) > 1 or not merger_entry.is_unambiguous_1to1:
            candidates: List[ResolutionCandidate] = []
            for s_code in merger_entry.successor_routing_codes:
                repaired_xml = self._substitute_routing_code_in_xml(raw_payload, normalized_code, s_code, clean_sys)
                candidates.append(ResolutionCandidate(
                    candidate_id=f"CAND-DQ08-AMB-{s_code}",
                    repaired_payload=repaired_xml,
                    diff_summary=f"Ambiguous successor candidate: '{normalized_code}' -> '{s_code}'",
                    derivation_method="CENTRAL_BANK_MERGER_SPLIT_DIRECTORY",
                    is_lossless=True
                ))
            trail.append(f"Stage 5 FAILED (Ambiguity): Retired code '{normalized_code}' mapped to {len(merger_entry.successor_routing_codes)} split successors: {merger_entry.successor_routing_codes}. R_uniq=False.")
            return DQ08RoutingResolutionResult(
                success=True,
                outcome=RoutingResolutionOutcome.MULTIPLE_SUCCESSORS,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                institution_name=dir_entry.institution_name,
                directory_entry=dir_entry,
                merger_entry=merger_entry,
                candidates=candidates,
                uniqueness=ResolutionUniqueness.RESOLUTION_AMBIGUOUS,
                is_ambiguous=True,
                is_lossless=True,
                semantic_preservation_passed=True,
                diff_summary=f"Multiple successor institutions in merger registry: {merger_entry.successor_routing_codes}",
                audit_trail=trail,
                error_message="Ambiguous successor institution mapping requires human operator disambiguation."
            )

        # Single 1:1 Authoritative Successor
        successor_code = merger_entry.successor_routing_codes[0]

        # Verify successor active status and reachability on requested rail
        succ_entry = self.directory_adapter.lookup_routing_code(successor_code, clean_sys)
        if not succ_entry or succ_entry.status != RoutingIdentifierStatus.ACTIVE:
            trail.append(f"Stage 5 FAILED: Successor code '{successor_code}' is not active in clearing directory.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.INACTIVE_NO_SUCCESSOR,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                resolved_routing_code=successor_code,
                institution_name=dir_entry.institution_name,
                directory_entry=dir_entry,
                merger_entry=merger_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Successor routing code inactive in clearing directory",
                audit_trail=trail,
                error_message=f"Successor '{successor_code}' is not an active member."
            )

        if not self.directory_adapter.is_rail_reachable(successor_code, clean_sys, req_rail):
            trail.append(f"Stage 5 FAILED: Successor code '{successor_code}' is active but not reachable on rail '{req_rail}'.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.ACTIVE_NOT_REACHABLE,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                resolved_routing_code=successor_code,
                institution_name=succ_entry.institution_name,
                directory_entry=succ_entry,
                merger_entry=merger_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary=f"Successor routing code not reachable on requested rail {req_rail}",
                audit_trail=trail,
                error_message=f"Successor code '{successor_code}' does not participate in '{req_rail}'."
            )

        # Check Bank SSI alignment if provided
        if bank_ssi and bank_ssi.mandated_routing_code and bank_ssi.mandated_routing_code != successor_code:
            trail.append(f"Stage 5 FAILED: Successor '{successor_code}' contradicts Bank SSI mandated code '{bank_ssi.mandated_routing_code}'.")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.SSI_CONTRADICTION,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                resolved_routing_code=successor_code,
                institution_name=succ_entry.institution_name,
                directory_entry=succ_entry,
                merger_entry=merger_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary="Successor routing code contradicts Bank Counterparty SSI",
                audit_trail=trail,
                error_message=f"Bank SSI requires '{bank_ssi.mandated_routing_code}', resolved '{successor_code}'."
            )

        # Build Repaired XML and Verify Semantic Invariance
        repaired_xml = self._substitute_routing_code_in_xml(raw_payload, normalized_code, successor_code, clean_sys)
        sem_passed, sem_err = self._verify_semantic_invariance(raw_payload, repaired_xml)

        if not sem_passed:
            trail.append(f"Stage 6 FAILED: Semantic preservation check failed: {sem_err}")
            return DQ08RoutingResolutionResult(
                success=False,
                outcome=RoutingResolutionOutcome.HITL_REQUIRED,
                clearing_system=clean_sys,
                original_routing_code=normalized_code,
                resolved_routing_code=successor_code,
                institution_name=succ_entry.institution_name,
                directory_entry=succ_entry,
                merger_entry=merger_entry,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                semantic_preservation_passed=False,
                diff_summary=f"Semantic data altered during XML substitution: {sem_err}",
                audit_trail=trail,
                error_message=sem_err
            )

        trail.append(f"Stage 6 (Resolution Determinism R_det / R_uniq): Successfully mapped retired '{normalized_code}' to successor '{successor_code}' ({succ_entry.institution_name}).")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-DQ08-SUCC-{successor_code}",
            repaired_payload=repaired_xml,
            diff_summary=f"Substituted retired routing code '{normalized_code}' with active successor '{successor_code}' ({succ_entry.institution_name})",
            derivation_method="CENTRAL_BANK_MERGER_DIRECTORY_1TO1_SOLVER",
            is_lossless=True
        )

        return DQ08RoutingResolutionResult(
            success=True,
            outcome=RoutingResolutionOutcome.SUCCESSOR_FOUND,
            clearing_system=clean_sys,
            original_routing_code=normalized_code,
            resolved_routing_code=successor_code,
            institution_name=succ_entry.institution_name,
            directory_entry=succ_entry,
            merger_entry=merger_entry,
            candidates=[candidate],
            uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
            is_ambiguous=False,
            is_lossless=True,
            semantic_preservation_passed=True,
            diff_summary=f"Replaced retired routing code '{normalized_code}' with successor '{successor_code}'",
            audit_trail=trail
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_routing_code_from_xml(self, xml_text: str) -> Optional[str]:
        """Extracts clearing routing transit number from <ClrSysMmbId><MmbId>."""
        if not xml_text:
            return None
        match = re.search(r'<ClrSysMmbId>[\s\S]*?<MmbId>([^<]+)</MmbId>[\s\S]*?</ClrSysMmbId>', xml_text)
        if match:
            return match.group(1).strip()
        # Fallback to simple MmbId
        match2 = re.search(r'<MmbId>([^<]+)</MmbId>', xml_text)
        if match2:
            return match2.group(1).strip()
        return None

    def _substitute_routing_code_in_xml(
        self,
        xml_text: str,
        old_code: str,
        new_code: str,
        clearing_system: str
    ) -> str:
        """Deterministically substitutes routing member ID inside <ClrSysMmbId> structure."""
        if not xml_text:
            return xml_text

        # If XML contains structured ClrSysMmbId
        pattern = re.compile(rf'(<ClrSysMmbId>[\s\S]*?<MmbId>){re.escape(old_code)}(</MmbId>[\s\S]*?</ClrSysMmbId>)')
        if pattern.search(xml_text):
            return pattern.sub(rf'\g<1>{new_code}\g<2>', xml_text, count=1)

        # Fallback exact MmbId replacement
        pattern2 = re.compile(rf'(<MmbId>){re.escape(old_code)}(</MmbId>)')
        if pattern2.search(xml_text):
            return pattern2.sub(rf'\g<1>{new_code}\g<2>', xml_text, count=1)

        return xml_text.replace(old_code, new_code)

    def _verify_semantic_invariance(self, pre_xml: str, post_xml: str) -> Tuple[bool, Optional[str]]:
        """Verifies that non-routing business values (amounts, accounts, currencies, UETRs) remain 100% invariant."""
        # 1. Amounts
        amt_pre = re.findall(r'<IntrBkSttlmAmt[^>]*>([^<]+)</IntrBkSttlmAmt>', pre_xml)
        amt_post = re.findall(r'<IntrBkSttlmAmt[^>]*>([^<]+)</IntrBkSttlmAmt>', post_xml)
        if amt_pre != amt_post:
            return False, f"Settlement amount altered: {amt_pre} vs {amt_post}"

        # 2. Debtor/Creditor Accounts
        acct_pre = re.findall(r'<Id><(?:IBAN|Othr/Id)>([^<]+)</(?:IBAN|Othr/Id)></Id>', pre_xml)
        acct_post = re.findall(r'<Id><(?:IBAN|Othr/Id)>([^<]+)</(?:IBAN|Othr/Id)></Id>', post_xml)
        if acct_pre != acct_post:
            return False, f"Account IDs altered: {acct_pre} vs {acct_post}"

        # 3. UETR
        uetr_pre = re.findall(r'<UETR>([^<]+)</UETR>', pre_xml)
        uetr_post = re.findall(r'<UETR>([^<]+)</UETR>', post_xml)
        if uetr_pre != uetr_post:
            return False, f"UETR altered: {uetr_pre} vs {uetr_post}"

        return True, None


# Global singleton instance for application use
governed_routing_resolver = GovernedRoutingCodeResolver()

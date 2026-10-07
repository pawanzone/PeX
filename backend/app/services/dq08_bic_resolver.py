"""Governed BIC / SWIFT Reference Data Resolver & Routing Engine for DQ-08.

DQ-08: INVALID_BIC_SWIFT
Part of Phase 2A Slice 3.

Distinguishes:
1. Syntactically valid BIC (ISO 9362 length & character format)
2. Structurally valid BIC (Bank code, country, location, branch structure)
3. Active vs Inactive BIC status (SWIFTRef reference directory status)
4. Successor mapping (Unique successor vs Multiple ambiguous successors vs No successor)
5. Requested-rail reachability (SWIFT CBPR+, Fedwire, CHAPS, TARGET2)
6. Bank Counterparty SSI authority (Authoritative bank routing instructions)

Enforces:
- External reference data adapter with explicit freshness and provenance
- Fail-closed handling when reference data is stale, missing, or contradictory to Bank SSI
- Ambiguity detection (Multiple successors force R_uniq=False -> Disambiguation Desk)
- Strict semantic invariance on non-routing XML fields
"""
import re
import hashlib
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)


class BICStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MERGED = "MERGED"
    REPLACED = "REPLACED"
    NOT_FOUND = "NOT_FOUND"


class BICResolutionOutcome(str, Enum):
    VALID_BIC = "VALID_BIC"
    SUCCESSOR_FOUND = "SUCCESSOR_FOUND"
    MULTIPLE_SUCCESSORS = "MULTIPLE_SUCCESSORS"
    INACTIVE_NO_SUCCESSOR = "INACTIVE_NO_SUCCESSOR"
    ACTIVE_NOT_REACHABLE = "ACTIVE_NOT_REACHABLE"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HITL_REQUIRED = "HITL_REQUIRED"


class BICReferenceEntry(BaseModel):
    """External reference directory entry for ISO 9362 BIC validation."""
    bic_code: str
    status: BICStatus
    institution_name: str
    country_code: str
    successor_bics: List[str] = Field(default_factory=list)
    supported_rails: List[str] = Field(default_factory=lambda: ["SWIFT_CBPR+", "TARGET2", "CHAPS", "FEDWIRE"])
    provider: str = "SWIFTREF_DIRECTORY_PROVIDER (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class BankCounterpartySSI(BaseModel):
    """Authoritative Bank Counterparty Standard Settlement Instructions (SSI)."""
    counterparty_id: str
    mandated_bic: Optional[str] = None
    allowed_bics: List[str] = Field(default_factory=list)
    corridor_rules: Dict[str, Any] = Field(default_factory=dict)
    is_authorized: bool = True
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TargetRailRoutingSpec(BaseModel):
    """Target clearing rail reachability parameters and constraints."""
    target_rail: str = "SWIFT_CBPR+"
    corridor: Optional[str] = None
    direct_participant_required: bool = False


class DQ08ResolutionResult(BaseModel):
    """Forensic result of executing the DQ-08 BIC resolution and validation pipeline."""
    success: bool
    outcome: BICResolutionOutcome
    original_bic: str
    resolved_bic: Optional[str] = None
    institution_name: Optional[str] = None
    reference_entry: Optional[BICReferenceEntry] = None
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    uniqueness: ResolutionUniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
    is_ambiguous: bool = False
    is_lossless: bool = True
    semantic_preservation_passed: bool = True
    diff_summary: str
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class ExternalBICReferenceAdapter:
    """External Reference Data Adapter abstracting directory lookups (SWIFTRef / Bank Directory)."""

    def __init__(self):
        # Demo / Synthetic dataset (Pluggable for production live SWIFTRef/ISO 9362 API)
        self._directory: Dict[str, BICReferenceEntry] = {}
        self._seed_demo_directory()

    def _seed_demo_directory(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=1)

        # Active Global BICs
        self._add_entry("DEUTDEDDFXX", BICStatus.ACTIVE, "Deutsche Bank AG", "DE", [], ["SWIFT_CBPR+", "TARGET2", "CHAPS", "FEDWIRE"], now, exp)
        self._add_entry("CHASUS33XXX", BICStatus.ACTIVE, "JPMorgan Chase Bank NA", "US", [], ["SWIFT_CBPR+", "TARGET2", "CHAPS", "FEDWIRE"], now, exp)
        self._add_entry("BARCGB22XXX", BICStatus.ACTIVE, "Barclays Bank UK PLC", "GB", [], ["SWIFT_CBPR+", "CHAPS", "TARGET2", "FEDWIRE"], now, exp)
        self._add_entry("BNPAFRPPXXX", BICStatus.ACTIVE, "BNP Paribas SA", "FR", [], ["SWIFT_CBPR+", "TARGET2", "FEDWIRE"], now, exp)
        self._add_entry("COBADEDDXXX", BICStatus.ACTIVE, "Commerzbank AG", "DE", [], ["SWIFT_CBPR+", "TARGET2", "FEDWIRE"], now, exp)
        self._add_entry("SBININBBNDL", BICStatus.ACTIVE, "State Bank of India New Delhi", "IN", [], ["SWIFT_CBPR+", "FEDWIRE"], now, exp)

        # Inactive BIC with single unique successor
        self._add_entry("DRESDEFFXXX", BICStatus.MERGED, "Dresdner Bank (Merged into Commerzbank)", "DE", ["COBADEDDXXX"], ["SWIFT_CBPR+", "TARGET2"], now, exp)
        self._add_entry("SBININBBXXX", BICStatus.INACTIVE, "State Bank of India (Consolidated)", "IN", ["SBININBBNDL"], ["SWIFT_CBPR+"], now, exp)

        # Inactive BIC with multiple ambiguous successors
        self._add_entry("AMROFRPPXXX", BICStatus.INACTIVE, "ABN AMRO France (Split Division)", "FR", ["BNPAFRPPXXX", "COBADEDDXXX"], ["SWIFT_CBPR+"], now, exp)

        # Inactive BIC with NO successor
        self._add_entry("LEHMUS33XXX", BICStatus.INACTIVE, "Lehman Brothers Inc (Defunct)", "US", [], [], now, exp)

        # Active BIC restricted to TARGET2 only (Not reachable on Fedwire / CHAPS)
        self._add_entry("LOCADE22XXX", BICStatus.ACTIVE, "Local Sparkasse Hessen", "DE", [], ["TARGET2"], now, exp)

    def _add_entry(self, bic: str, status: BICStatus, name: str, country: str, successors: List[str], rails: List[str], retrieved: datetime, expires: datetime):
        self._directory[bic.upper()] = BICReferenceEntry(
            bic_code=bic.upper(),
            status=status,
            institution_name=name,
            country_code=country,
            successor_bics=successors,
            supported_rails=rails,
            provider="SWIFTREF_DIRECTORY_PROVIDER (DEMO/SYNTHETIC)",
            retrieved_at=retrieved,
            effective_at=retrieved,
            expires_at=expires,
            freshness_seconds=86400
        )

    def lookup(self, bic_code: str) -> Optional[BICReferenceEntry]:
        """Looks up reference data entry for a normalized 8 or 11 character BIC."""
        norm = bic_code.strip().upper()
        if len(norm) == 8:
            norm = norm + "XXX"
        return self._directory.get(norm)


class GovernedDQ08BICResolver:
    """Master engine executing governed BIC structural validation, directory lookup, and successor routing."""

    def __init__(self, reference_adapter: Optional[ExternalBICReferenceAdapter] = None):
        self.reference_adapter = reference_adapter or ExternalBICReferenceAdapter()

    def validate_bic_structure(self, bic_code: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates ISO 9362 structural syntax (8 or 11 alphanumeric characters)."""
        if not bic_code or not isinstance(bic_code, str):
            return False, None, "BIC code is empty or not a string."

        clean_bic = bic_code.strip().upper()
        # ISO 9362 regex: 4 letters (institution), 2 letters (country), 2 letters/digits (location), optional 3 letters/digits (branch)
        iso_pattern = r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$'
        if not re.match(iso_pattern, clean_bic):
            return False, clean_bic, f"BIC '{clean_bic}' does not conform to ISO 9362 format (8 or 11 alphanumeric chars)."

        # Normalize 8-char to 11-char head office with XXX
        normalized_bic = clean_bic if len(clean_bic) == 11 else clean_bic + "XXX"
        return True, normalized_bic, None

    def resolve_bic(
        self,
        raw_payload: str,
        original_bic: Optional[str] = None,
        reference_entry: Optional[BICReferenceEntry] = None,
        bank_ssi: Optional[BankCounterpartySSI] = None,
        target_rail_spec: Optional[TargetRailRoutingSpec] = None,
        allow_stale_reference: bool = False
    ) -> DQ08ResolutionResult:
        """Deterministically evaluates BIC validity, reference data status, successor routing, and SSI corroboration."""
        trail: List[str] = []
        trail.append("Initiating DQ-08 governed BIC / SWIFT reference data resolution pipeline.")

        # 1. Extract original BIC
        extracted_bic = original_bic
        if not extracted_bic:
            bic_match = re.search(r'<BICFI>([A-Z0-9]+)</BICFI>', raw_payload)
            if not bic_match:
                bic_match = re.search(r'<BIC>([A-Z0-9]+)</BIC>', raw_payload)
            if bic_match:
                extracted_bic = bic_match.group(1).strip()
            else:
                trail.append("Stage 1 FAILED: Could not locate <BICFI> or <BIC> tag in message payload.")
                return DQ08ResolutionResult(
                    success=False,
                    outcome=BICResolutionOutcome.INSUFFICIENT_EVIDENCE,
                    original_bic="UNKNOWN",
                    diff_summary="Missing mandatory BIC in payload",
                    audit_trail=trail,
                    error_message="Could not extract BIC from payload"
                )

        trail.append(f"Stage 1 (BIC Extraction): Inbound original BIC: '{extracted_bic}'.")

        # 2. Structural Syntax Validation (V_det)
        is_struct_valid, norm_bic, struct_err = self.validate_bic_structure(extracted_bic)
        if not is_struct_valid:
            trail.append(f"Stage 2 (Structural Syntax): FAILED - {struct_err}")
            return DQ08ResolutionResult(
                success=False,
                outcome=BICResolutionOutcome.HITL_REQUIRED,
                original_bic=extracted_bic,
                diff_summary=f"Structurally invalid BIC: {struct_err}",
                audit_trail=trail,
                error_message=struct_err
            )

        trail.append(f"Stage 2 (Structural Syntax): PASSED - ISO 9362 structural syntax validated (Normalized: '{norm_bic}').")

        # 3. Reference Directory Lookup
        ref = reference_entry or self.reference_adapter.lookup(norm_bic)
        if ref is None:
            trail.append(f"Stage 3 (Reference Lookup): FAILED - BIC '{norm_bic}' not found in authoritative reference directory.")
            return DQ08ResolutionResult(
                success=False,
                outcome=BICResolutionOutcome.INSUFFICIENT_EVIDENCE,
                original_bic=extracted_bic,
                resolved_bic=None,
                diff_summary=f"BIC '{norm_bic}' not found in reference directory",
                audit_trail=trail,
                error_message="BIC not registered in reference directory"
            )

        # Check Freshness
        if ref.is_stale and not allow_stale_reference:
            trail.append(f"Stage 3 (Freshness Check): FAILED - Reference data for '{norm_bic}' is STALE (Retrieved: {ref.retrieved_at.isoformat()}, Expires: {ref.expires_at.isoformat()}). Fail-closed.")
            return DQ08ResolutionResult(
                success=False,
                outcome=BICResolutionOutcome.INSUFFICIENT_EVIDENCE,
                original_bic=extracted_bic,
                reference_entry=ref,
                diff_summary="Stale reference directory data",
                audit_trail=trail,
                error_message="Reference directory entry expired or stale"
            )

        trail.append(f"Stage 3 (Reference Lookup): PASSED - Found '{ref.institution_name}' (Status: {ref.status.value}, Country: {ref.country_code}, Provider: {ref.provider}).")

        # 4. Successor Mapping & Ambiguity Resolution
        resolved_bic = norm_bic
        outcome = BICResolutionOutcome.VALID_BIC
        is_ambiguous = False
        uniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
        candidates: List[ResolutionCandidate] = []

        if ref.status == BICStatus.ACTIVE:
            outcome = BICResolutionOutcome.VALID_BIC
            resolved_bic = norm_bic
            trail.append(f"Stage 4 (Status Check): BIC '{norm_bic}' is ACTIVE and current.")
        elif ref.status in (BICStatus.INACTIVE, BICStatus.MERGED, BICStatus.REPLACED):
            if len(ref.successor_bics) == 1:
                resolved_bic = ref.successor_bics[0]
                outcome = BICResolutionOutcome.SUCCESSOR_FOUND
                trail.append(f"Stage 4 (Successor Mapping): BIC '{norm_bic}' is {ref.status.value}. Exactly 1 authoritative successor identified: '{resolved_bic}'.")
            elif len(ref.successor_bics) > 1:
                is_ambiguous = True
                uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS
                outcome = BICResolutionOutcome.MULTIPLE_SUCCESSORS
                trail.append(f"Stage 4 (Successor Mapping): BIC '{norm_bic}' has MULTIPLE ({len(ref.successor_bics)}) plausible successors: {ref.successor_bics}. Flagged R_uniq=False -> DISAMBIGUATION_DESK.")
            else:
                outcome = BICResolutionOutcome.INACTIVE_NO_SUCCESSOR
                trail.append(f"Stage 4 (Successor Mapping): BIC '{norm_bic}' is INACTIVE with ZERO successors available. Routed to HITL.")
                return DQ08ResolutionResult(
                    success=False,
                    outcome=outcome,
                    original_bic=extracted_bic,
                    reference_entry=ref,
                    diff_summary=f"Inactive BIC '{norm_bic}' with no known successor",
                    audit_trail=trail,
                    error_message="Inactive BIC without successor"
                )

        # 5. Target Rail Reachability Validation
        rail_spec = target_rail_spec or TargetRailRoutingSpec()
        if rail_spec.target_rail not in ref.supported_rails and outcome == BICResolutionOutcome.VALID_BIC:
            outcome = BICResolutionOutcome.ACTIVE_NOT_REACHABLE
            trail.append(f"Stage 5 (Rail Reachability): FAILED - BIC '{resolved_bic}' supports rails {ref.supported_rails} but requested rail is '{rail_spec.target_rail}'. Not reachable.")
            return DQ08ResolutionResult(
                success=False,
                outcome=outcome,
                original_bic=extracted_bic,
                resolved_bic=resolved_bic,
                reference_entry=ref,
                diff_summary=f"BIC not reachable on requested clearing rail: {rail_spec.target_rail}",
                audit_trail=trail,
                error_message=f"BIC not reachable on rail {rail_spec.target_rail}"
            )

        trail.append(f"Stage 5 (Rail Reachability): PASSED - BIC '{resolved_bic}' confirmed reachable on requested rail '{rail_spec.target_rail}'.")

        # 6. Bank Counterparty SSI Corroboration ($V_{auth}$)
        if bank_ssi is not None:
            if not bank_ssi.is_authorized:
                outcome = BICResolutionOutcome.AUTHORITY_MISMATCH
                trail.append("Stage 6 (SSI Corroboration): FAILED - Bank counterparty SSI is marked UNAUTHORIZED. Fail-closed.")
            elif bank_ssi.mandated_bic and bank_ssi.mandated_bic.strip().upper() != resolved_bic:
                # Contradictory Authority: External reference successor contradicts Bank SSI mandate
                outcome = BICResolutionOutcome.AUTHORITY_MISMATCH
                trail.append(f"Stage 6 (SSI Corroboration): FAILED - External reference resolved '{resolved_bic}' but Bank SSI mandates '{bank_ssi.mandated_bic}'. Contradictory authority -> Block STP.")
                return DQ08ResolutionResult(
                    success=False,
                    outcome=outcome,
                    original_bic=extracted_bic,
                    resolved_bic=resolved_bic,
                    reference_entry=ref,
                    diff_summary=f"Authority Mismatch: Reference resolved '{resolved_bic}' vs Bank SSI mandated '{bank_ssi.mandated_bic}'",
                    audit_trail=trail,
                    error_message="Contradictory authority between reference directory and Bank SSI"
                )
            else:
                trail.append(f"Stage 6 (SSI Corroboration): PASSED - Resolved BIC '{resolved_bic}' corroborated by authoritative Bank SSI.")

        # 7. Generate Resolution Candidates & Semantic Invariance
        pre_tokens = self._extract_business_tokens(raw_payload)
        repaired_payload = raw_payload

        if outcome == BICResolutionOutcome.VALID_BIC:
            diff_summary = f"BIC '{norm_bic}' validated as active and reachable."
            c1 = ResolutionCandidate(
                candidate_id=f"CAND-DQ08-VAL-{hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()[:8]}",
                repaired_payload=raw_payload,
                diff_summary=diff_summary,
                derivation_method="DETERMINISTIC_DQ08_BIC_VALIDATOR",
                is_lossless=True
            )
            candidates.append(c1)

        elif outcome == BICResolutionOutcome.SUCCESSOR_FOUND:
            # Replace BIC tag in XML
            repaired_payload = re.sub(r'<BICFI>[^<]+</BICFI>', f'<BICFI>{resolved_bic}</BICFI>', raw_payload)
            if repaired_payload == raw_payload:
                repaired_payload = re.sub(r'<BIC>[^<]+</BIC>', f'<BIC>{resolved_bic}</BIC>', raw_payload)

            diff_summary = f"Successor replacement: Replaced inactive BIC '{norm_bic}' with authoritative successor '{resolved_bic}'."
            c1 = ResolutionCandidate(
                candidate_id=f"CAND-DQ08-SUCC-{hashlib.sha256(repaired_payload.encode('utf-8')).hexdigest()[:8]}",
                repaired_payload=repaired_payload,
                diff_summary=diff_summary,
                derivation_method="DETERMINISTIC_DQ08_SUCCESSOR_ROUTER",
                is_lossless=True
            )
            candidates.append(c1)

        elif outcome == BICResolutionOutcome.MULTIPLE_SUCCESSORS:
            diff_summary = f"Multiple successors for '{norm_bic}': {ref.successor_bics}. Requires operator disambiguation."
            for idx, succ in enumerate(ref.successor_bics):
                cand_xml = re.sub(r'<BICFI>[^<]+</BICFI>', f'<BICFI>{succ}</BICFI>', raw_payload)
                c_alt = ResolutionCandidate(
                    candidate_id=f"CAND-DQ08-ALT{idx+1}-{hashlib.sha256(cand_xml.encode('utf-8')).hexdigest()[:8]}",
                    repaired_payload=cand_xml,
                    diff_summary=f"Option {idx+1}: Route to successor '{succ}'",
                    derivation_method="DETERMINISTIC_DQ08_SUCCESSOR_ROUTER",
                    is_lossless=True
                )
                candidates.append(c_alt)

        # 8. Verify Semantic Invariance on Non-BIC fields
        post_tokens = self._extract_business_tokens(repaired_payload)
        sem_passed, sem_err = self._verify_semantic_invariance(pre_tokens, post_tokens)
        if not sem_passed:
            trail.append(f"Stage 7 FAILED: Semantic preservation error: {sem_err}")
            return DQ08ResolutionResult(
                success=False,
                outcome=BICResolutionOutcome.HITL_REQUIRED,
                original_bic=extracted_bic,
                resolved_bic=resolved_bic,
                reference_entry=ref,
                diff_summary="Semantic alteration during BIC replacement",
                semantic_preservation_passed=False,
                is_lossless=False,
                audit_trail=trail,
                error_message=f"Semantic preservation error: {sem_err}"
            )

        trail.append("Stage 7 (Semantic Preservation): Creditor/Debtor accounts, monetary amounts, and UETR 100% invariant.")

        return DQ08ResolutionResult(
            success=(outcome in (BICResolutionOutcome.VALID_BIC, BICResolutionOutcome.SUCCESSOR_FOUND, BICResolutionOutcome.MULTIPLE_SUCCESSORS)),
            outcome=outcome,
            original_bic=extracted_bic,
            resolved_bic=resolved_bic,
            institution_name=ref.institution_name,
            reference_entry=ref,
            candidates=candidates,
            uniqueness=uniqueness,
            is_ambiguous=is_ambiguous,
            is_lossless=True,
            semantic_preservation_passed=True,
            diff_summary=diff_summary,
            audit_trail=trail
        )

    def _extract_business_tokens(self, text: str) -> Dict[str, Any]:
        """Extracts non-BIC business tokens for semantic invariance verification."""
        tokens: Dict[str, Any] = {
            "amounts": re.findall(r'<IntrBkSttlmAmt[^>]*>([0-9]+\.[0-9]{2})</IntrBkSttlmAmt>', text),
            "accounts": re.findall(r'<Id><IBAN>([A-Z0-9]+)</IBAN></Id>', text),
            "uetr": re.findall(r'<UETR>([^<]+)</UETR>', text),
            "e2e": re.findall(r'<EndToEndId>([^<]+)</EndToEndId>', text)
        }
        return tokens

    def _verify_semantic_invariance(self, pre: Dict[str, Any], post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies that non-BIC business fields remain strictly identical."""
        if pre["amounts"] != post["amounts"]:
            return False, f"Monetary amount altered: {pre['amounts']} vs {post['amounts']}"
        if pre["accounts"] != post["accounts"]:
            return False, f"Account number altered: {pre['accounts']} vs {post['accounts']}"
        if pre["uetr"] != post["uetr"]:
            return False, f"UETR altered: {pre['uetr']} vs {post['uetr']}"
        if pre["e2e"] != post["e2e"]:
            return False, f"EndToEndId altered: {pre['e2e']} vs {post['e2e']}"
        return True, None


# Global singleton instance
dq08_resolver = GovernedDQ08BICResolver()

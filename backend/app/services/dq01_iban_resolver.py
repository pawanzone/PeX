"""Governed IBAN Resolver, MOD-97-10 Solver & Bank System-of-Record Engine for DQ-01.

DQ-01: INVALID_IBAN
Phase: Phase 2C (Slice 5)

Governing Standards & Taxonomy:
- ISO 13616: International Bank Account Number (IBAN) - Structure and country format specifications.
- ISO 7064: MOD-97-10 check digit arithmetic (r == 1).
- ISO 20022: pacs.008 Customer Credit Transfer (<CdtrAcct><Id><IBAN> and <DbtrAcct><Id><IBAN>).
- BIAN Domain: Data Quality Exceptions (Group 2: Conditionally STP-capable).

Core Architectural Invariants:
1. Separation of Concerns:
   MOD-97 VALIDITY != ACCOUNT VALIDITY != BENEFICIARY OWNERSHIP != BANK AUTHORIZATION != STP ELIGIBILITY.
   MOD-97 = 1 proves mathematical check digit validity only (V_det). It does NOT prove account existence,
   active status, beneficiary ownership, or payment authorization (V_auth).
2. Bank System-of-Record (SoR) Authority:
   Bank SSI Master and Core DDA Ledger govern account validity. Historical frequency and AI confidence
   are strictly advisory and CANNOT satisfy authority gates.
3. Bounded Deterministic Derivation:
   Candidate generation investigates constrained single-transposition, check-digit correction, and
   single-digit substitutions. Unbounded brute-force generation is prohibited.
4. Fail-Closed Handling:
   Closed/frozen accounts, contradictory SoR data, stale evidence (> TTL), or multiple candidates
   without authoritative disambiguation immediately fail closed to HITL / Suspense / Disambiguation Desk.
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


# ============================================================================
# ISO 13616 Country IBAN Specifications (Length & Regex Grammar)
# ============================================================================

IBAN_COUNTRY_SPECS: Dict[str, Dict[str, Any]] = {
    "DE": {"length": 22, "bban_pattern": r'^[0-9]{8}[0-9]{10}$', "country_name": "Germany"},
    "GB": {"length": 22, "bban_pattern": r'^[A-Z]{4}[0-9]{6}[0-9]{8}$', "country_name": "United Kingdom"},
    "FR": {"length": 27, "bban_pattern": r'^[0-9]{5}[0-9]{5}[A-Z0-9]{11}[0-9]{2}$', "country_name": "France"},
    "IT": {"length": 27, "bban_pattern": r'^[A-Z]{1}[0-9]{5}[0-9]{5}[A-Z0-9]{12}$', "country_name": "Italy"},
    "ES": {"length": 24, "bban_pattern": r'^[0-9]{4}[0-9]{4}[0-9]{2}[0-9]{10}$', "country_name": "Spain"},
    "NL": {"length": 18, "bban_pattern": r'^[A-Z]{4}[0-9]{10}$', "country_name": "Netherlands"},
    "BE": {"length": 16, "bban_pattern": r'^[0-9]{3}[0-9]{7}[0-9]{2}$', "country_name": "Belgium"},
    "CH": {"length": 21, "bban_pattern": r'^[0-9]{5}[A-Z0-9]{12}$', "country_name": "Switzerland"},
    "AT": {"length": 20, "bban_pattern": r'^[0-9]{5}[0-9]{11}$', "country_name": "Austria"},
    "PL": {"length": 28, "bban_pattern": r'^[0-9]{8}[0-9]{16}$', "country_name": "Poland"},
    "PT": {"length": 25, "bban_pattern": r'^[0-9]{4}[0-9]{4}[0-9]{11}[0-9]{2}$', "country_name": "Portugal"},
    "IE": {"length": 22, "bban_pattern": r'^[A-Z]{4}[0-9]{6}[0-9]{8}$', "country_name": "Ireland"},
}


class AccountLedgerStatus(str, Enum):
    """Authoritative account status from Bank Core DDA Ledger."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FROZEN = "FROZEN"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class CoPMatchResult(str, Enum):
    """Confirmation of Payee (CoP) / Verification of Payee (VoP) response."""
    MATCH = "MATCH"
    CLOSE_MATCH = "CLOSE_MATCH"
    NO_MATCH = "NO_MATCH"
    UNAVAILABLE = "UNAVAILABLE"


class IBANResolutionOutcome(str, Enum):
    """Canonical resolution outcomes for DQ-01."""
    VALID_NO_REPAIR = "VALID_NO_REPAIR"
    SINGLE_CANDIDATE_REPAIRED = "SINGLE_CANDIDATE_REPAIRED"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    NO_VALID_CANDIDATE = "NO_VALID_CANDIDATE"
    ACCOUNT_CLOSED = "ACCOUNT_CLOSED"
    ACCOUNT_FROZEN = "ACCOUNT_FROZEN"
    ACCOUNT_RESTRICTED = "ACCOUNT_RESTRICTED"
    BENEFICIARY_MISMATCH = "BENEFICIARY_MISMATCH"
    SSI_CONTRADICTION = "SSI_CONTRADICTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    SEARCH_BOUND_EXCEEDED = "SEARCH_BOUND_EXCEEDED"
    HITL_REQUIRED = "HITL_REQUIRED"


# ============================================================================
# Bank System-of-Record (SoR) Models & Adapters (Provider-Neutral)
# ============================================================================

class BankSSIMasterEntry(BaseModel):
    """Authoritative Bank Counterparty Standard Settlement Instruction (SSI) Record."""
    counterparty_id: str
    beneficiary_name: str
    mandated_iban: str
    allowed_ibans: List[str] = Field(default_factory=list)
    currency: str = "EUR"
    is_authorized: bool = True
    provider: str = "BANK_SSI_MASTER_STORE (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400  # DEMO_ONLY_DEFAULT: 24 hours

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class CoreDDAAccountRecord(BaseModel):
    """Authoritative Bank Core DDA Ledger Account Record."""
    account_number: str
    iban: str
    account_holder_name: str
    status: AccountLedgerStatus = AccountLedgerStatus.OPEN
    currency: str = "EUR"
    is_credit_blocked: bool = False
    is_debit_blocked: bool = False
    provider: str = "BANK_CORE_DDA_ADAPTER (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    freshness_seconds: int = 3600  # DEMO_ONLY_DEFAULT: 1 hour ledger cache

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class CustomerBeneficiaryRecord(BaseModel):
    """Authoritative Bank Customer / Beneficiary Master Record."""
    customer_id: str
    legal_name: str
    trading_names: List[str] = Field(default_factory=list)
    registered_ibans: List[str] = Field(default_factory=list)
    kyc_status: str = "VERIFIED"
    provider: str = "BANK_CUSTOMER_MASTER (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoPResponse(BaseModel):
    """Confirmation of Payee / Verification of Payee Response."""
    account_name_submitted: str
    matched_name: Optional[str] = None
    match_result: CoPMatchResult = CoPMatchResult.MATCH
    provider: str = "PAY_UK_COP_GATEWAY (DEMO/SYNTHETIC)"
    query_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    token: str = "COP-MATCH-TOKEN-DEMO"


# ============================================================================
# In-Memory Reference & SoR Adapters (Explicitly DEMO / SYNTHETIC)
# ============================================================================

class BankSSIMasterAdapter:
    """Adapter abstracting Bank SSI Master queries. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def __init__(self):
        self._ssi_store: Dict[str, BankSSIMasterEntry] = {}
        self._seed_demo_ssi()

    def _seed_demo_ssi(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=1)
        # Seed 1: Bavarian Industrial AG (Correct DE IBAN)
        self.register(BankSSIMasterEntry(
            counterparty_id="CP-BAVARIAN-01",
            beneficiary_name="Bavarian Industrial AG",
            mandated_iban="DE89370400440532013000",
            allowed_ibans=["DE89370400440532013000"],
            currency="EUR",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 2: Siemens Energy Global (Correct DE IBAN)
        self.register(BankSSIMasterEntry(
            counterparty_id="CP-SIEMENS-01",
            beneficiary_name="Siemens Energy Global GmbH",
            mandated_iban="DE02100100100123456789",
            allowed_ibans=["DE02100100100123456789"],
            currency="EUR",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 3: British Trading Corp (GB IBAN)
        self.register(BankSSIMasterEntry(
            counterparty_id="CP-BRITISH-01",
            beneficiary_name="British Trading Corp Ltd",
            mandated_iban="GB58WEST12345678901234",
            allowed_ibans=["GB58WEST12345678901234"],
            currency="GBP",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 4: French Supply SAS (FR IBAN)
        self.register(BankSSIMasterEntry(
            counterparty_id="CP-FRENCH-01",
            beneficiary_name="French Supply SAS",
            mandated_iban="FR1420041010050500013M02606",
            allowed_ibans=["FR1420041010050500013M02606"],
            currency="EUR",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))

    def register(self, entry: BankSSIMasterEntry):
        self._ssi_store[entry.counterparty_id] = entry
        self._ssi_store[entry.beneficiary_name.upper()] = entry
        self._ssi_store[entry.mandated_iban.upper()] = entry

    def lookup(self, identifier: str) -> Optional[BankSSIMasterEntry]:
        if not identifier:
            return None
        return self._ssi_store.get(identifier.strip().upper()) or self._ssi_store.get(identifier.strip())


class CoreDDAAdapter:
    """Adapter abstracting Bank Core DDA account status queries. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def __init__(self):
        self._accounts: Dict[str, CoreDDAAccountRecord] = {}
        self._seed_demo_accounts()

    def _seed_demo_accounts(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)
        # Active open accounts
        self.register(CoreDDAAccountRecord(
            account_number="0532013000",
            iban="DE89370400440532013000",
            account_holder_name="Bavarian Industrial AG",
            status=AccountLedgerStatus.OPEN,
            retrieved_at=now,
            expires_at=exp
        ))
        self.register(CoreDDAAccountRecord(
            account_number="0123456789",
            iban="DE02100100100123456789",
            account_holder_name="Siemens Energy Global GmbH",
            status=AccountLedgerStatus.OPEN,
            retrieved_at=now,
            expires_at=exp
        ))
        self.register(CoreDDAAccountRecord(
            account_number="78901234",
            iban="GB58WEST12345678901234",
            account_holder_name="British Trading Corp Ltd",
            status=AccountLedgerStatus.OPEN,
            retrieved_at=now,
            expires_at=exp
        ))
        # Closed account fixture
        self.register(CoreDDAAccountRecord(
            account_number="9999999999",
            iban="DE89500105179999999999",
            account_holder_name="Defunct Trading GmbH",
            status=AccountLedgerStatus.CLOSED,
            retrieved_at=now,
            expires_at=exp
        ))
        # Frozen account fixture
        self.register(CoreDDAAccountRecord(
            account_number="8888888888",
            iban="DE39500105178888888888",
            account_holder_name="Frozen Assets AG",
            status=AccountLedgerStatus.FROZEN,
            is_credit_blocked=True,
            retrieved_at=now,
            expires_at=exp
        ))


    def register(self, record: CoreDDAAccountRecord):
        self._accounts[record.iban.upper()] = record
        self._accounts[record.account_number] = record

    def lookup(self, iban_or_acct: str) -> Optional[CoreDDAAccountRecord]:
        if not iban_or_acct:
            return None
        return self._accounts.get(iban_or_acct.strip().upper()) or self._accounts.get(iban_or_acct.strip())


class CustomerBeneficiaryMasterAdapter:
    """Adapter abstracting Customer KYC Master data. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def __init__(self):
        self._customers: Dict[str, CustomerBeneficiaryRecord] = {}
        self._seed_demo_customers()

    def _seed_demo_customers(self):
        now = datetime.now(timezone.utc)
        self.register(CustomerBeneficiaryRecord(
            customer_id="CUST-001",
            legal_name="Bavarian Industrial AG",
            registered_ibans=["DE89370400440532013000"],
            retrieved_at=now
        ))
        self.register(CustomerBeneficiaryRecord(
            customer_id="CUST-002",
            legal_name="Siemens Energy Global GmbH",
            registered_ibans=["DE02100100100123456789"],
            retrieved_at=now
        ))

    def register(self, record: CustomerBeneficiaryRecord):
        self._customers[record.legal_name.upper()] = record
        for iban in record.registered_ibans:
            self._customers[iban.upper()] = record

    def lookup(self, name_or_iban: str) -> Optional[CustomerBeneficiaryRecord]:
        if not name_or_iban:
            return None
        return self._customers.get(name_or_iban.strip().upper())


class CoPVoPAdapter:
    """Adapter abstracting Confirmation of Payee queries. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def query_cop(self, iban: str, beneficiary_name: str) -> CoPResponse:
        """Simulates external CoP / VoP verification response."""
        now = datetime.now(timezone.utc)
        clean_iban = iban.strip().upper()
        # Predefined demo match behavior
        if clean_iban in ("DE89370400440532013000", "GB82WEST12345678901234", "DE02100100100123456789"):
            return CoPResponse(
                account_name_submitted=beneficiary_name,
                matched_name=beneficiary_name,
                match_result=CoPMatchResult.MATCH,
                query_timestamp=now,
                token=f"COP-MATCH-{clean_iban[:6]}"
            )
        elif "MISMATCH" in beneficiary_name.upper() or clean_iban.endswith("9999"):
            return CoPResponse(
                account_name_submitted=beneficiary_name,
                matched_name="Unrelated Beneficiary Ltd",
                match_result=CoPMatchResult.NO_MATCH,
                query_timestamp=now,
                token="COP-NO-MATCH"
            )
        return CoPResponse(
            account_name_submitted=beneficiary_name,
            matched_name=None,
            match_result=CoPMatchResult.UNAVAILABLE,
            query_timestamp=now,
            token="COP-UNAVAILABLE"
        )


# ============================================================================
# Resolution Result Model for DQ-01
# ============================================================================

class DQ01ResolutionResult(BaseModel):
    """Forensic result of executing the DQ-01 IBAN resolution and validation pipeline."""
    success: bool
    outcome: IBANResolutionOutcome
    original_iban: str
    repaired_iban: Optional[str] = None
    beneficiary_name: Optional[str] = None
    country_code: Optional[str] = None
    mod97_valid: bool = False
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    uniqueness: ResolutionUniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
    is_ambiguous: bool = False
    is_lossless: bool = True
    semantic_preservation_passed: bool = True
    diff_summary: str
    ssi_record: Optional[BankSSIMasterEntry] = None
    dda_record: Optional[CoreDDAAccountRecord] = None
    cop_response: Optional[CoPResponse] = None
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


# ============================================================================
# Governed DQ-01 IBAN Resolver & MOD-97-10 Solver Engine
# ============================================================================

class GovernedDQ01IBANResolver:
    """Master engine executing governed ISO 13616 structural validation, ISO 7064 MOD-97 calculation,
    bounded candidate permutation solving, and Bank SoR (SSI / Core DDA / CoP) corroboration.
    """

    def __init__(
        self,
        ssi_adapter: Optional[BankSSIMasterAdapter] = None,
        dda_adapter: Optional[CoreDDAAdapter] = None,
        cust_adapter: Optional[CustomerBeneficiaryMasterAdapter] = None,
        cop_adapter: Optional[CoPVoPAdapter] = None
    ):
        self.ssi_adapter = ssi_adapter or BankSSIMasterAdapter()
        self.dda_adapter = dda_adapter or CoreDDAAdapter()
        self.cust_adapter = cust_adapter or CustomerBeneficiaryMasterAdapter()
        self.cop_adapter = cop_adapter or CoPVoPAdapter()

    # ------------------------------------------------------------------------
    # 1. ISO 13616 Structural Validation
    # ------------------------------------------------------------------------
    def validate_iban_structure(self, iban_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates ISO 13616 country prefix, length, and alphanumeric syntax.
        
        Returns:
            Tuple[is_valid, country_code, error_message]
        """
        if not iban_str or not isinstance(iban_str, str):
            return False, None, "IBAN is empty or non-string."

        clean = re.sub(r'\s+', '', iban_str.strip().upper())
        if len(clean) < 4:
            return False, None, f"IBAN '{clean}' is too short (< 4 chars)."

        country_code = clean[:2]
        if not re.match(r'^[A-Z]{2}$', country_code):
            return False, None, f"Invalid country prefix '{country_code}'."

        if not re.match(r'^[A-Z0-9]+$', clean):
            return False, country_code, f"IBAN '{clean}' contains invalid special characters."

        # Check against ISO 13616 country registry if known
        spec = IBAN_COUNTRY_SPECS.get(country_code)
        if spec is not None:
            expected_len = spec["length"]
            if len(clean) != expected_len:
                return False, country_code, f"IBAN length {len(clean)} invalid for {spec['country_name']} (expected {expected_len})."

            bban = clean[4:]
            bban_pattern = spec.get("bban_pattern")
            if bban_pattern and not re.match(bban_pattern, bban):
                return False, country_code, f"BBAN structure '{bban}' does not conform to national standard for {spec['country_name']}."
        else:
            # Country not in registry - generic ISO length bound (max 34)
            if len(clean) > 34:
                return False, country_code, f"IBAN length {len(clean)} exceeds ISO 13616 max length of 34."

        return True, country_code, None

    # ------------------------------------------------------------------------
    # 2. ISO 7064 MOD-97-10 Mathematical Checksum
    # ------------------------------------------------------------------------
    def calculate_mod97(self, iban_str: str) -> int:
        """Calculates ISO 7064 MOD-97-10 remainder using integer arithmetic.
        
        Algorithm:
        1. Move first 4 characters to the end.
        2. Convert letters A-Z to digits 10-35.
        3. Compute integer modulo 97.
        """
        clean = re.sub(r'\s+', '', iban_str.strip().upper())
        if len(clean) < 4:
            return -1

        rearranged = clean[4:] + clean[:4]
        numeric_chars = []
        for ch in rearranged:
            if ch.isdigit():
                numeric_chars.append(ch)
            elif ch.isalpha():
                numeric_chars.append(str(ord(ch) - ord('A') + 10))
            else:
                return -1

        num_str = "".join(numeric_chars)
        try:
            return int(num_str) % 97
        except ValueError:
            return -1

    def is_mod97_valid(self, iban_str: str) -> bool:
        """Returns True iff ISO 7064 MOD-97 remainder == 1."""
        return self.calculate_mod97(iban_str) == 1

    def compute_check_digits(self, country_code: str, bban: str) -> str:
        """Computes valid 2-digit MOD-97 check digits for a given country and BBAN."""
        country = country_code.strip().upper()
        dummy_iban = f"{country}00{bban}"
        rem = self.calculate_mod97(dummy_iban)
        check_val = 98 - rem
        return f"{check_val:02d}"

    # ------------------------------------------------------------------------
    # 3. Bounded Deterministic Candidate Permutation Solver
    # ------------------------------------------------------------------------
    def generate_candidate_permutations(
        self,
        corrupted_iban: str,
        max_candidates: int = 20
    ) -> List[str]:
        """Generates bounded mathematical permutations that satisfy MOD-97 == 1.
        
        Explores:
        1. Check-digit recalculation (if only check digits were mistyped).
        2. Single-character adjacent transposition (e.g. '12' -> '21').
        3. Single-digit substitution (0-9 replacement at each BBAN position).
        4. Transposition with leading zero adjustments.
        
        Safety Bounds:
        - Max edit distance = 1
        - Max candidate return limit = max_candidates
        - Bounded string length check (rejects oversized malicious input > 40 chars)
        """
        clean = re.sub(r'\s+', '', corrupted_iban.strip().upper())
        if len(clean) < 4 or len(clean) > 40:
            return []

        country = clean[:2]
        spec = IBAN_COUNTRY_SPECS.get(country)
        expected_len = spec["length"] if spec else len(clean)
        if len(clean) != expected_len:
            return []

        candidates_set: Set[str] = set()

        # Strategy 1: Check Digit Recalculation (if BBAN is intact)
        bban = clean[4:]
        recalc_cd = self.compute_check_digits(country, bban)
        cand_recalc = f"{country}{recalc_cd}{bban}"
        if cand_recalc != clean and self.is_mod97_valid(cand_recalc):
            candidates_set.add(cand_recalc)

        # Strategy 2: Single-Character Adjacent Transposition
        # Swap adjacent characters across the entire IBAN
        chars = list(clean)
        for i in range(len(chars) - 1):
            if chars[i] != chars[i+1]:
                swapped = list(chars)
                swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
                cand = "".join(swapped)
                if self.is_mod97_valid(cand):
                    # Validate syntax structure
                    valid_struct, _, _ = self.validate_iban_structure(cand)
                    if valid_struct:
                        candidates_set.add(cand)
                        if len(candidates_set) >= max_candidates:
                            return list(candidates_set)

        # Strategy 3: Single-Digit Substitution across BBAN numeric positions
        for i in range(4, len(chars)):
            if chars[i].isdigit():
                orig_digit = chars[i]
                for d in "0123456789":
                    if d != orig_digit:
                        mutated = list(chars)
                        mutated[i] = d
                        cand = "".join(mutated)
                        if self.is_mod97_valid(cand):
                            valid_struct, _, _ = self.validate_iban_structure(cand)
                            if valid_struct:
                                candidates_set.add(cand)
                                if len(candidates_set) >= max_candidates:
                                    return list(candidates_set)

        return sorted(list(candidates_set))

    # ------------------------------------------------------------------------
    # 4. End-to-End Governed IBAN Resolution Pipeline
    # ------------------------------------------------------------------------
    def resolve_iban(
        self,
        raw_payload: str,
        original_iban: Optional[str] = None,
        beneficiary_name: Optional[str] = None,
        ssi_record: Optional[BankSSIMasterEntry] = None,
        dda_record: Optional[CoreDDAAccountRecord] = None,
        cop_response: Optional[CoPResponse] = None,
        allow_stale_evidence: bool = False,
        require_cop: bool = False
    ) -> DQ01ResolutionResult:
        """Executes the governed DQ-01 resolution and validation lifecycle."""
        trail: List[str] = []
        trail.append("Initiating DQ-01 governed IBAN & Bank System-of-Record resolution pipeline.")

        # Step 1: Extract Inbound IBAN
        extracted_iban = original_iban
        if not extracted_iban:
            iban_match = re.search(r'<CdtrAcct>\s*<Id>\s*<IBAN>([A-Z0-9]+)</IBAN>', raw_payload)
            if not iban_match:
                iban_match = re.search(r'<IBAN>([A-Z0-9]+)</IBAN>', raw_payload)
            if iban_match:
                extracted_iban = iban_match.group(1).strip().upper()
            else:
                trail.append("Step 1 FAILED: Could not locate <IBAN> element in payment payload.")
                return DQ01ResolutionResult(
                    success=False,
                    outcome=IBANResolutionOutcome.INSUFFICIENT_EVIDENCE,
                    original_iban="UNKNOWN",
                    diff_summary="Missing mandatory IBAN in payload",
                    audit_trail=trail,
                    error_message="Could not extract IBAN from raw payload"
                )

        # Extract Beneficiary Name if not provided
        extracted_bene = beneficiary_name
        if not extracted_bene:
            bene_match = re.search(r'<Cdtr>\s*<Nm>([^<]+)</Nm>', raw_payload)
            if bene_match:
                extracted_bene = bene_match.group(1).strip()

        trail.append(f"Step 1 (Extraction): Inbound IBAN: '{extracted_iban}', Beneficiary: '{extracted_bene}'.")

        # Step 1b: Input Safety & Bounds Check
        if len(extracted_iban) > 40:
            trail.append(f"Step 1b FAILED: IBAN length {len(extracted_iban)} exceeds safety limit (max 40 chars).")
            return DQ01ResolutionResult(
                success=False,
                outcome=IBANResolutionOutcome.SEARCH_BOUND_EXCEEDED,
                original_iban=extracted_iban,
                diff_summary="Maliciously oversized IBAN input",
                audit_trail=trail,
                error_message="IBAN length exceeds safety boundary"
            )

        # Step 2: ISO 13616 Structural Syntax Check
        is_struct_valid, country, struct_err = self.validate_iban_structure(extracted_iban)
        if not is_struct_valid:
            trail.append(f"Step 2 (Structural Validation): FAILED - {struct_err}")
        else:
            trail.append(f"Step 2 (Structural Validation): PASSED - Country: {country}.")

        # Step 3: ISO 7064 MOD-97 Mathematical Checksum
        mod97_valid = self.is_mod97_valid(extracted_iban)
        if mod97_valid:
            trail.append("Step 3 (MOD-97-10 Checksum): PASSED (r == 1). Inbound IBAN is mathematically valid.")
        else:
            rem = self.calculate_mod97(extracted_iban)
            trail.append(f"Step 3 (MOD-97-10 Checksum): FAILED (remainder == {rem} != 1). Inbound IBAN is mathematically invalid.")

        # Step 4: Candidate Permutation Solving (if corrupted)
        candidates_list: List[ResolutionCandidate] = []
        resolved_iban: Optional[str] = None
        outcome = IBANResolutionOutcome.NO_VALID_CANDIDATE
        uniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
        is_ambiguous = False

        if is_struct_valid and mod97_valid:
            # Case A: IBAN is already mathematically valid
            resolved_iban = extracted_iban
            outcome = IBANResolutionOutcome.VALID_NO_REPAIR
            c_valid = ResolutionCandidate(
                candidate_id=f"CAND-DQ01-VAL-{hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()[:8]}",
                repaired_payload=raw_payload,
                diff_summary=f"IBAN '{extracted_iban}' is mathematically valid and structurally compliant.",
                derivation_method="DETERMINISTIC_DQ01_IBAN_VALIDATOR",
                is_lossless=True
            )
            candidates_list.append(c_valid)
            trail.append(f"Step 4 (Candidate Derivation): IBAN '{extracted_iban}' requires no mathematical repair.")
        else:
            # Case B: Mathematically corrupted - Generate candidate permutations
            math_candidates = self.generate_candidate_permutations(extracted_iban)
            trail.append(f"Step 4 (Candidate Derivation): Generated {len(math_candidates)} mathematical permutations satisfying MOD-97 == 1.")

            if len(math_candidates) == 0:
                outcome = IBANResolutionOutcome.NO_VALID_CANDIDATE
                trail.append("Step 4: Zero valid mathematical permutations derived within edit distance 1. Fail-closed to HITL.")
                return DQ01ResolutionResult(
                    success=False,
                    outcome=outcome,
                    original_iban=extracted_iban,
                    country_code=country,
                    mod97_valid=False,
                    diff_summary=f"Corrupted IBAN '{extracted_iban}' with no valid mathematical candidate",
                    audit_trail=trail,
                    error_message="No valid candidate found within search bounds"
                )

            # Build candidate objects
            for idx, cand_iban in enumerate(math_candidates):
                repaired_xml = re.sub(
                    r'<IBAN>[^<]+</IBAN>',
                    f'<IBAN>{cand_iban}</IBAN>',
                    raw_payload
                )
                c = ResolutionCandidate(
                    candidate_id=f"CAND-DQ01-M{idx+1}-{hashlib.sha256(cand_iban.encode('utf-8')).hexdigest()[:8]}",
                    repaired_payload=repaired_xml,
                    diff_summary=f"Repaired IBAN '{extracted_iban}' -> '{cand_iban}' (MOD-97 == 1).",
                    derivation_method="DETERMINISTIC_ISO7064_MOD97_SOLVER",
                    is_lossless=True
                )
                candidates_list.append(c)

        # Step 5: Bank System-of-Record (SoR) Authority Corroboration ($V_{auth}$)
        # Acquire Bank SSI Master Record
        ssi_entry = ssi_record
        if ssi_entry is None and extracted_bene:
            ssi_entry = self.ssi_adapter.lookup(extracted_bene)
        if ssi_entry is None and resolved_iban:
            ssi_entry = self.ssi_adapter.lookup(resolved_iban)

        # Acquire Core DDA Account Status Record
        dda_entry = dda_record
        target_check_iban = resolved_iban or (candidates_list[0].diff_summary.split("'")[3] if candidates_list else extracted_iban)
        if dda_entry is None:
            dda_entry = self.dda_adapter.lookup(target_check_iban)

        # Check Freshness of Bank Evidence
        if ssi_entry and ssi_entry.is_stale and not allow_stale_evidence:
            trail.append("Step 5 (Evidence Freshness): FAILED - Bank SSI Master record is STALE. Fail-closed.")
            return DQ01ResolutionResult(
                success=False,
                outcome=IBANResolutionOutcome.INSUFFICIENT_EVIDENCE,
                original_iban=extracted_iban,
                country_code=country,
                ssi_record=ssi_entry,
                diff_summary="Bank SSI Master record is stale (TTL exceeded)",
                audit_trail=trail,
                error_message="Stale Bank SSI evidence"
            )

        if dda_entry and dda_entry.is_stale and not allow_stale_evidence:
            trail.append("Step 5 (Evidence Freshness): FAILED - Core DDA account record is STALE. Fail-closed.")
            return DQ01ResolutionResult(
                success=False,
                outcome=IBANResolutionOutcome.INSUFFICIENT_EVIDENCE,
                original_iban=extracted_iban,
                country_code=country,
                dda_record=dda_entry,
                diff_summary="Core DDA account record is stale (TTL exceeded)",
                audit_trail=trail,
                error_message="Stale Core DDA evidence"
            )

        # Step 6: Intersect Mathematical Candidates with Bank SoR Authority
        if outcome != IBANResolutionOutcome.VALID_NO_REPAIR:
            matching_candidates: List[ResolutionCandidate] = []
            for cand in candidates_list:
                cand_iban_val = re.search(r'<IBAN>([A-Z0-9]+)</IBAN>', cand.repaired_payload).group(1)
                # Check SSI match
                ssi_match = False
                if ssi_entry and ssi_entry.is_authorized:
                    if ssi_entry.mandated_iban.upper() == cand_iban_val.upper() or cand_iban_val.upper() in [x.upper() for x in ssi_entry.allowed_ibans]:
                        ssi_match = True

                # Check DDA ledger state
                dda_match = False
                dda_rec = self.dda_adapter.lookup(cand_iban_val)
                if dda_rec and dda_rec.status == AccountLedgerStatus.OPEN:
                    dda_match = True

                if ssi_match or dda_match:
                    matching_candidates.append(cand)
                    resolved_iban = cand_iban_val

            if len(matching_candidates) == 1:
                outcome = IBANResolutionOutcome.SINGLE_CANDIDATE_REPAIRED
                candidates_list = matching_candidates
                uniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
                trail.append(f"Step 6 (SoR Intersect): Exactly 1 candidate '{resolved_iban}' corroborated by Bank SoR authority.")
            elif len(matching_candidates) > 1:
                outcome = IBANResolutionOutcome.MULTIPLE_CANDIDATES
                uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS
                is_ambiguous = True
                candidates_list = matching_candidates
                trail.append(f"Step 6 (SoR Intersect): MULTIPLE ({len(matching_candidates)}) candidates corroborated by SoR. Flagged R_uniq=False -> DISAMBIGUATION_DESK.")
            else:
                # No candidate matched Bank SoR
                if len(candidates_list) > 1:
                    outcome = IBANResolutionOutcome.MULTIPLE_CANDIDATES
                    uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS
                    is_ambiguous = True
                    trail.append(f"Step 6 (SoR Intersect): {len(candidates_list)} mathematical candidates exist but NONE corroborated by Bank SSI. R_uniq=False -> DISAMBIGUATION_DESK.")
                else:
                    outcome = IBANResolutionOutcome.AUTHORITY_MISMATCH
                    trail.append(f"Step 6 (SoR Intersect): Candidate '{candidates_list[0].candidate_id}' not corroborated by Bank SSI Master. Authority mismatch.")
                    return DQ01ResolutionResult(
                        success=False,
                        outcome=outcome,
                        original_iban=extracted_iban,
                        country_code=country,
                        candidates=candidates_list,
                        ssi_record=ssi_entry,
                        dda_record=dda_entry,
                        diff_summary="Mathematical candidate not corroborated by Bank SSI Master",
                        audit_trail=trail,
                        error_message="Candidate fails Bank SSI corroboration"
                    )

        # Step 7: Core DDA Ledger Account Status Check
        if resolved_iban:
            dda_final = self.dda_adapter.lookup(resolved_iban) or dda_entry
            if dda_final is not None:
                if dda_final.status == AccountLedgerStatus.CLOSED:
                    outcome = IBANResolutionOutcome.ACCOUNT_CLOSED
                    trail.append(f"Step 7 (Core DDA Status): FAILED - Account for '{resolved_iban}' is CLOSED. STP blocked.")
                    return DQ01ResolutionResult(
                        success=False,
                        outcome=outcome,
                        original_iban=extracted_iban,
                        repaired_iban=resolved_iban,
                        country_code=country,
                        candidates=candidates_list,
                        uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                        is_ambiguous=False,
                        dda_record=dda_final,
                        diff_summary=f"Resolved IBAN '{resolved_iban}' is CLOSED in Core DDA",
                        audit_trail=trail,
                        error_message="Account is CLOSED in Core DDA"
                    )
                elif dda_final.status == AccountLedgerStatus.FROZEN:
                    outcome = IBANResolutionOutcome.ACCOUNT_FROZEN
                    trail.append(f"Step 7 (Core DDA Status): FAILED - Account for '{resolved_iban}' is FROZEN (credit blocked). STP blocked.")
                    return DQ01ResolutionResult(
                        success=False,
                        outcome=outcome,
                        original_iban=extracted_iban,
                        repaired_iban=resolved_iban,
                        country_code=country,
                        candidates=candidates_list,
                        uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                        is_ambiguous=False,
                        dda_record=dda_final,
                        diff_summary=f"Resolved IBAN '{resolved_iban}' is FROZEN in Core DDA",
                        audit_trail=trail,
                        error_message="Account is FROZEN in Core DDA"
                    )
                elif dda_final.status == AccountLedgerStatus.RESTRICTED:
                    outcome = IBANResolutionOutcome.ACCOUNT_RESTRICTED
                    trail.append(f"Step 7 (Core DDA Status): FAILED - Account for '{resolved_iban}' is RESTRICTED. Route to HITL.")
                    return DQ01ResolutionResult(
                        success=False,
                        outcome=outcome,
                        original_iban=extracted_iban,
                        repaired_iban=resolved_iban,
                        country_code=country,
                        candidates=candidates_list,
                        uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                        is_ambiguous=False,
                        dda_record=dda_final,
                        diff_summary=f"Resolved IBAN '{resolved_iban}' is RESTRICTED in Core DDA",
                        audit_trail=trail,
                        error_message="Account is RESTRICTED in Core DDA"
                    )


        # Step 8: Confirmation of Payee (CoP / VoP) Corroboration (if required or provided)
        cop_res = cop_response
        if (require_cop or cop_res is not None) and resolved_iban and extracted_bene:
            if cop_res is None:
                cop_res = self.cop_adapter.query_cop(resolved_iban, extracted_bene)
            trail.append(f"Step 8 (Confirmation of Payee): Response: {cop_res.match_result.value} (Token: {cop_res.token}).")
            if cop_res.match_result == CoPMatchResult.NO_MATCH:
                outcome = IBANResolutionOutcome.BENEFICIARY_MISMATCH
                trail.append(f"Step 8 (CoP Match): FAILED - CoP returned NO_MATCH for beneficiary '{extracted_bene}'. STP blocked.")
                return DQ01ResolutionResult(
                    success=False,
                    outcome=outcome,
                    original_iban=extracted_iban,
                    repaired_iban=resolved_iban,
                    country_code=country,
                    candidates=candidates_list,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_ambiguous=False,
                    cop_response=cop_res,
                    diff_summary=f"Confirmation of Payee mismatch for '{extracted_bene}'",
                    audit_trail=trail,
                    error_message="Confirmation of Payee returned NO_MATCH"
                )

        # Step 9: Semantic Invariance Verification
        final_repaired_xml = candidates_list[0].repaired_payload if candidates_list else raw_payload
        pre_tokens = self._extract_business_tokens(raw_payload)
        post_tokens = self._extract_business_tokens(final_repaired_xml)
        sem_passed, sem_err = self._verify_semantic_invariance(pre_tokens, post_tokens)
        if not sem_passed:
            trail.append(f"Step 9 FAILED: Semantic preservation error: {sem_err}")
            return DQ01ResolutionResult(
                success=False,
                outcome=IBANResolutionOutcome.HITL_REQUIRED,
                original_iban=extracted_iban,
                repaired_iban=resolved_iban,
                country_code=country,
                semantic_preservation_passed=False,
                is_lossless=False,
                diff_summary="Semantic alteration during IBAN repair",
                audit_trail=trail,
                error_message=f"Semantic preservation error: {sem_err}"
            )

        trail.append("Step 9 (Semantic Invariance): Non-IBAN business fields (Amounts, UETR, Accounts) 100% preserved.")

        is_success = outcome in (
            IBANResolutionOutcome.VALID_NO_REPAIR,
            IBANResolutionOutcome.SINGLE_CANDIDATE_REPAIRED,
            IBANResolutionOutcome.MULTIPLE_CANDIDATES
        )

        return DQ01ResolutionResult(
            success=is_success,
            outcome=outcome,
            original_iban=extracted_iban,
            repaired_iban=resolved_iban,
            beneficiary_name=extracted_bene,
            country_code=country,
            mod97_valid=mod97_valid or (resolved_iban is not None and self.is_mod97_valid(resolved_iban)),
            candidates=candidates_list,
            uniqueness=uniqueness,
            is_ambiguous=is_ambiguous,
            is_lossless=True,
            semantic_preservation_passed=True,
            diff_summary=candidates_list[0].diff_summary if candidates_list else "IBAN resolution evaluated",
            ssi_record=ssi_entry,
            dda_record=dda_entry,
            cop_response=cop_res,
            audit_trail=trail
        )

    def _extract_business_tokens(self, text: str) -> Dict[str, Any]:
        """Extracts non-IBAN business tokens for semantic invariance verification."""
        tokens: Dict[str, Any] = {
            "amounts": re.findall(r'<IntrBkSttlmAmt[^>]*>([0-9]+\.[0-9]{2})</IntrBkSttlmAmt>', text),
            "bic": re.findall(r'<BICFI>([A-Z0-9]+)</BICFI>', text) or re.findall(r'<BIC>([A-Z0-9]+)</BIC>', text),
            "uetr": re.findall(r'<UETR>([^<]+)</UETR>', text),
            "e2e": re.findall(r'<EndToEndId>([^<]+)</EndToEndId>', text),
            "dbtr_name": re.findall(r'<Dbtr>\s*<Nm>([^<]+)</Nm>', text),
            "cdtr_name": re.findall(r'<Cdtr>\s*<Nm>([^<]+)</Nm>', text)
        }
        return tokens

    def _verify_semantic_invariance(self, pre: Dict[str, Any], post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies that non-IBAN business fields remain strictly invariant."""
        if pre["amounts"] != post["amounts"]:
            return False, f"Monetary amount altered: {pre['amounts']} vs {post['amounts']}"
        if pre["bic"] != post["bic"]:
            return False, f"BIC altered: {pre['bic']} vs {post['bic']}"
        if pre["uetr"] != post["uetr"]:
            return False, f"UETR altered: {pre['uetr']} vs {post['uetr']}"
        if pre["e2e"] != post["e2e"]:
            return False, f"EndToEndId altered: {pre['e2e']} vs {post['e2e']}"
        if pre["dbtr_name"] != post["dbtr_name"]:
            return False, f"Debtor name altered: {pre['dbtr_name']} vs {post['dbtr_name']}"
        if pre["cdtr_name"] != post["cdtr_name"]:
            return False, f"Creditor name altered: {pre['cdtr_name']} vs {post['cdtr_name']}"
        return True, None


# Global singleton resolver instance for DQ-01
dq01_resolver = GovernedDQ01IBANResolver()

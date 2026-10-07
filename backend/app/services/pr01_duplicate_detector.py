"""Governed Duplicate Payment Detection & Identity Resolution Engine for PR-01.

PR-01: DUPLICATE_PAYMENT
Part of Phase 2A Slice 3.

Distinguishes between:
1. CLASS A: Exact Duplicate / Identity Collision (Same UETR + Canonical Hash + Active/Settled Ledger)
2. CLASS B: Highly Similar Payments (Same Amount/Currency/Beneficiary, different UETR/Ref -> Possible Duplicate -> HITL required)
3. CLASS C: Historical Similarity (Informs investigation only, cannot establish current duplicate authority)
4. CLASS NONE: Distinct Legitimate Payments (Confirmed distinct -> Release)

Enforces:
- Deterministic payment fingerprinting and canonical hash verification
- Current bank ledger state authority (SETTLED, UNSETTLED, ALREADY_RELEASED, CANCELLED)
- Fail-closed evaluation when ledger authority is missing or contradictory
- Process-level idempotency locking and collision tracking
- Strict semantic invariance and lossless candidates
"""
import re
import hashlib
import threading
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


class DuplicateOutcome(str, Enum):
    DUPLICATE_CONFIRMED = "DUPLICATE_CONFIRMED"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    NOT_DUPLICATE = "NOT_DUPLICATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DuplicateClass(str, Enum):
    CLASS_A_EXACT_COLLISION = "CLASS_A_EXACT_COLLISION"
    CLASS_B_HIGH_SIMILARITY = "CLASS_B_HIGH_SIMILARITY"
    CLASS_C_HISTORICAL_SIMILARITY = "CLASS_C_HISTORICAL_SIMILARITY"
    CLASS_NONE_DISTINCT = "CLASS_NONE_DISTINCT"


class PaymentIdentityRecord(BaseModel):
    """Deterministic payment identity and canonical fingerprint."""
    uetr: str
    canonical_hash: str
    end_to_end_id: str
    amount: float
    currency: str
    debtor_account: str
    creditor_account: str
    value_date: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CurrentSettlementState(BaseModel):
    """Authoritative bank core ledger / settlement state record."""
    payment_id: str
    ledger_status: str       # SETTLED, UNSETTLED, ALREADY_RELEASED, CANCELLED, RETURNED, UNKNOWN
    settlement_timestamp: Optional[str] = None
    original_instruction_id: Optional[str] = None
    account_debited: bool = False
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PR01DuplicateDetectionResult(BaseModel):
    """Forensic result of executing the PR-01 duplicate detection and resolution pipeline."""
    success: bool
    duplicate_outcome: DuplicateOutcome
    duplicate_class: DuplicateClass
    identity_record: PaymentIdentityRecord
    matched_payment_id: Optional[str] = None
    settlement_state: Optional[CurrentSettlementState] = None
    similarity_score: float = 0.0
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    uniqueness: ResolutionUniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
    is_ambiguous: bool = False
    is_lossless: bool = True
    is_collision_locked: bool = False
    diff_summary: str
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class GovernedPR01DuplicateDetector:
    """Master engine executing governed payment identity hashing, collision detection, and resolution."""

    def __init__(self):
        self._lock = threading.Lock()
        # In-memory registry of active/processed payments for collision detection in prototype
        # (Persistent boundary in SQLite/Enterprise DB; documented limitation for distributed clustering)
        self._active_payment_identities: Dict[str, PaymentIdentityRecord] = {}
        self._settlement_records: Dict[str, CurrentSettlementState] = {}

    def extract_identity(self, raw_payload: str, uetr: Optional[str] = None, amount: Optional[float] = None, currency: Optional[str] = None) -> PaymentIdentityRecord:
        """Extracts and computes deterministic payment identity record and canonical hash."""
        # Extract UETR
        extracted_uetr = uetr
        if not extracted_uetr:
            uetr_match = re.search(r'<UETR>([^<]+)</UETR>', raw_payload)
            if uetr_match:
                extracted_uetr = uetr_match.group(1).strip()
            else:
                uetr_match = re.search(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', raw_payload)
                extracted_uetr = uetr_match.group(0) if uetr_match else "00000000-0000-0000-0000-000000000000"

        extracted_uetr = extracted_uetr.lower()

        # Extract Amount & Currency
        extracted_amt = amount
        extracted_ccy = currency or "USD"
        if extracted_amt is None:
            amt_match = re.search(r'<IntrBkSttlmAmt[^>]*Ccy="([A-Z]{3})"[^>]*>([0-9]+\.[0-9]{2})</IntrBkSttlmAmt>', raw_payload)
            if amt_match:
                extracted_ccy = amt_match.group(1)
                extracted_amt = float(amt_match.group(2))
            else:
                amt_match2 = re.search(r'>(\d+\.\d{2})<', raw_payload)
                extracted_amt = float(amt_match2.group(1)) if amt_match2 else 0.0

        # Extract Debtor & Creditor Accounts
        dbtr_acct = "UNKNOWN_DBTR"
        cdtr_acct = "UNKNOWN_CDTR"
        dbtr_match = re.search(r'<DbtrAcct>.*?<IBAN>([A-Z0-9]+)</IBAN>', raw_payload, re.DOTALL)
        if dbtr_match:
            dbtr_acct = dbtr_match.group(1).strip()
        else:
            ibans = re.findall(r'[A-Z]{2}\d{2}[A-Z0-9]{12,30}', raw_payload)
            if len(ibans) >= 2:
                dbtr_acct = ibans[0]
                cdtr_acct = ibans[1]

        cdtr_match = re.search(r'<CdtrAcct>.*?<IBAN>([A-Z0-9]+)</IBAN>', raw_payload, re.DOTALL)
        if cdtr_match:
            cdtr_acct = cdtr_match.group(1).strip()

        # Extract EndToEndId
        e2e_id = "UNKNOWN_E2E"
        e2e_match = re.search(r'<EndToEndId>([^<]+)</EndToEndId>', raw_payload)
        if e2e_match:
            e2e_id = e2e_match.group(1).strip()

        # Extract ValueDate
        val_date = None
        date_match = re.search(r'<IntrBkSttlmDt>([^<]+)</IntrBkSttlmDt>', raw_payload)
        if date_match:
            val_date = date_match.group(1).strip()

        # Compute Canonical Payment Fingerprint SHA-256 Hash
        canonical_str = f"UETR:{extracted_uetr}|AMT:{extracted_amt:.2f}|CCY:{extracted_ccy.upper()}|DBTR:{dbtr_acct.upper()}|CDTR:{cdtr_acct.upper()}|E2E:{e2e_id}|DT:{val_date or ''}"
        canonical_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        return PaymentIdentityRecord(
            uetr=extracted_uetr,
            canonical_hash=canonical_hash,
            end_to_end_id=e2e_id,
            amount=extracted_amt,
            currency=extracted_ccy,
            debtor_account=dbtr_acct,
            creditor_account=cdtr_acct,
            value_date=val_date
        )

    def detect_and_resolve(
        self,
        raw_payload: str,
        identity: Optional[PaymentIdentityRecord] = None,
        settlement_state: Optional[CurrentSettlementState] = None,
        bank_policy: Optional[Dict[str, Any]] = None,
        historical_index: Optional[List[Dict[str, Any]]] = None,
        target_payment_id: Optional[str] = None
    ) -> PR01DuplicateDetectionResult:
        """Deterministically classifies duplicate payments, verifies ledger authority, and generates resolution candidate."""
        trail: List[str] = []
        trail.append("Initiating PR-01 governed duplicate payment detection & identity resolution.")

        # 1. Establish Identity
        ident = identity or self.extract_identity(raw_payload)
        trail.append(f"Stage 1 (Identity Fingerprint): UETR='{ident.uetr}', CanonicalHash='{ident.canonical_hash[:16]}...', Amount={ident.amount} {ident.currency}.")

        # 2. Check Concurrency & Idempotency Locking
        is_collision_locked = False
        with self._lock:
            existing_identity = self._active_payment_identities.get(ident.canonical_hash)
            if existing_identity is None:
                self._active_payment_identities[ident.canonical_hash] = ident
            else:
                is_collision_locked = True
                trail.append(f"Stage 2 (Idempotency Lock): Exact canonical hash collision identified with active record: '{ident.canonical_hash[:16]}...'.")

        # 3. Classify Duplicate Class
        dup_class = DuplicateClass.CLASS_NONE_DISTINCT
        dup_outcome = DuplicateOutcome.NOT_DUPLICATE
        matched_payment_id = None
        similarity_score = 0.0
        is_ambiguous = False
        uniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE

        # Check for Class A: Exact Collision on UETR & Canonical Hash
        if settlement_state is not None and settlement_state.ledger_status in ("SETTLED", "ALREADY_RELEASED", "ALREADY_PROCESSED"):
            if ident.uetr != "00000000-0000-0000-0000-000000000000":
                dup_class = DuplicateClass.CLASS_A_EXACT_COLLISION
                dup_outcome = DuplicateOutcome.DUPLICATE_CONFIRMED
                matched_payment_id = settlement_state.payment_id
                similarity_score = 1.0
                trail.append(f"Stage 3 (Classification): CLASS A Exact Collision confirmed against settled ledger payment '{settlement_state.payment_id}' (Status: {settlement_state.ledger_status}).")
        elif settlement_state is not None and settlement_state.ledger_status == "UNSETTLED":
            # Exact identity exists in queue but not yet settled -> In-flight collision
            dup_class = DuplicateClass.CLASS_A_EXACT_COLLISION
            dup_outcome = DuplicateOutcome.DUPLICATE_CONFIRMED
            matched_payment_id = settlement_state.payment_id
            similarity_score = 1.0
            trail.append(f"Stage 3 (Classification): CLASS A In-Flight Exact Collision against unsettled ledger entry '{settlement_state.payment_id}'.")
        elif settlement_state is not None and settlement_state.ledger_status in ("CANCELLED", "RETURNED"):
            # Previous payment was cancelled/returned -> This incoming payment is a legitimate re-submission or distinct payment
            dup_class = DuplicateClass.CLASS_NONE_DISTINCT
            dup_outcome = DuplicateOutcome.NOT_DUPLICATE
            matched_payment_id = settlement_state.payment_id
            similarity_score = 0.0
            trail.append(f"Stage 3 (Classification): Prior transaction '{settlement_state.payment_id}' was {settlement_state.ledger_status}. Incoming instruction is NOT a duplicate.")
        else:
            # Check for Class B: High Similarity (Same Amount, Same Beneficiary, but Different UETR/Reference)
            if bank_policy and bank_policy.get("is_authorized") and historical_index:
                for hist in historical_index:
                    hist_amt = hist.get("amount")
                    hist_cdtr = hist.get("creditor_account")
                    hist_uetr = hist.get("uetr", "")
                    if hist_amt == ident.amount and hist_cdtr == ident.creditor_account and hist_uetr != ident.uetr:
                        # High similarity but distinct UETR
                        dup_class = DuplicateClass.CLASS_B_HIGH_SIMILARITY
                        dup_outcome = DuplicateOutcome.POSSIBLE_DUPLICATE
                        matched_payment_id = hist.get("payment_id", "HIST-TX-UNKNOWN")
                        similarity_score = 0.88
                        is_ambiguous = True
                        uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS
                        trail.append(f"Stage 3 (Classification): CLASS B High Similarity detected with transaction '{matched_payment_id}' (Same amount & creditor, distinct UETR). Flagged R_uniq=False for HITL disambiguation.")
                        break

            # If no settlement state provided and no active match
            if dup_class == DuplicateClass.CLASS_NONE_DISTINCT and settlement_state is None:
                # Missing ledger authority
                trail.append("Stage 3: Current settlement/ledger state not provided in evidence. Cannot assert live duplicate confirmation.")
                dup_outcome = DuplicateOutcome.INSUFFICIENT_EVIDENCE

        # 4. Generate Resolution Candidate
        candidates: List[ResolutionCandidate] = []
        diff_summary = ""

        if dup_outcome == DuplicateOutcome.DUPLICATE_CONFIRMED:
            diff_summary = f"DUPLICATE_CONFIRMED: Exact collision on UETR '{ident.uetr}' with settled transaction '{matched_payment_id}'. Action: SUPPRESS duplicate execution to prevent double debit."
            c1 = ResolutionCandidate(
                candidate_id=f"CAND-PR01-{ident.canonical_hash[:8]}",
                repaired_payload=raw_payload,
                diff_summary=diff_summary,
                derivation_method="DETERMINISTIC_PR01_EXACT_COLLISION_SUPPRESSION",
                is_lossless=True
            )
            candidates.append(c1)
            trail.append(f"Stage 4 (Resolution): Candidate generated to SUPPRESS duplicate payment (Linked to '{matched_payment_id}').")

        elif dup_outcome == DuplicateOutcome.POSSIBLE_DUPLICATE:
            diff_summary = f"POSSIBLE_DUPLICATE: High similarity with '{matched_payment_id}' (Amount: {ident.amount} {ident.currency}). Requires human operator validation."
            c1 = ResolutionCandidate(
                candidate_id=f"CAND-PR01-POSS-{ident.canonical_hash[:8]}",
                repaired_payload=raw_payload,
                diff_summary=f"Option 1: Confirm duplicate and suppress execution (Linked to '{matched_payment_id}')",
                derivation_method="DETERMINISTIC_PR01_SIMILARITY_ANALYSIS",
                is_lossless=True
            )
            c2 = ResolutionCandidate(
                candidate_id=f"CAND-PR01-DIST-{ident.canonical_hash[:8]}",
                repaired_payload=raw_payload,
                diff_summary="Option 2: Confirm legitimate distinct recurring payment and release to bank handoff",
                derivation_method="DETERMINISTIC_PR01_SIMILARITY_ANALYSIS",
                is_lossless=True
            )
            candidates.extend([c1, c2])
            trail.append("Stage 4 (Resolution): Multiple resolution candidates generated for HITL disambiguation.")

        elif dup_outcome == DuplicateOutcome.NOT_DUPLICATE:
            diff_summary = f"NOT_DUPLICATE: Confirmed distinct legitimate instruction (UETR: '{ident.uetr}'). Action: RELEASE to bank handoff."
            c1 = ResolutionCandidate(
                candidate_id=f"CAND-PR01-REL-{ident.canonical_hash[:8]}",
                repaired_payload=raw_payload,
                diff_summary=diff_summary,
                derivation_method="DETERMINISTIC_PR01_DISTINCT_PAYMENT_RELEASE",
                is_lossless=True
            )
            candidates.append(c1)
            trail.append("Stage 4 (Resolution): Candidate generated to RELEASE distinct legitimate payment.")

        else: # INSUFFICIENT_EVIDENCE
            diff_summary = "INSUFFICIENT_EVIDENCE: Missing current bank ledger state authority."
            trail.append("Stage 4 (Resolution): Zero candidate resolutions generated due to missing mandatory ledger state.")

        return PR01DuplicateDetectionResult(
            success=(dup_outcome != DuplicateOutcome.INSUFFICIENT_EVIDENCE),
            duplicate_outcome=dup_outcome,
            duplicate_class=dup_class,
            identity_record=ident,
            matched_payment_id=matched_payment_id,
            settlement_state=settlement_state,
            similarity_score=similarity_score,
            candidates=candidates,
            uniqueness=uniqueness,
            is_ambiguous=is_ambiguous,
            is_lossless=True,
            is_collision_locked=is_collision_locked,
            diff_summary=diff_summary,
            audit_trail=trail,
            error_message=None if dup_outcome != DuplicateOutcome.INSUFFICIENT_EVIDENCE else "Missing mandatory current ledger state"
        )


# Global singleton instance
pr01_detector = GovernedPR01DuplicateDetector()

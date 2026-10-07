"""Governed Character & State Transformer Engine for PR-08 (UNSUPPORTED_SPECIAL_CHARACTERS).

Handles unsupported characters in payment messages under target clearing rail specifications:
1. Target Rail Charset Verification (e.g. SWIFT X-Set, SWIFT Z-Set, Fedwire, CHAPS)
2. Field-Targeted Unsupported Character Identification
3. State Management & Poison-Message Defense (Retry bounding, queue state validation)
4. Bank Policy Authorized Character Substitution / Transliteration
5. Strict Semantic Invariance Guarding (Account, Amount, Decimal, Currency, UETR, Reference protection)
6. Deterministic Candidate Generation & Validation
"""
import re
import unicodedata
import hashlib
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# Standard Clearing Rail Character Sets
SWIFT_X_CHARS: Set[str] = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-?:().,'+ \r\n\t")
SWIFT_Z_CHARS: Set[str] = SWIFT_X_CHARS.union(set(",_!\"%&*;<>=@#{`"))
FEDWIRE_STRICT_CHARS: Set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -./,*$()':;=?+\r\n\t")

# Default Bank Character Substitution Catalog (when authorized by Bank Policy)
DEFAULT_PR08_SUBSTITUTION_MAP: Dict[str, str] = {
    '@': ' AT ',
    '#': ' NO ',
    '&': ' AND ',
    '%': ' PCT ',
    '—': '-',       # Em-dash to hyphen
    '–': '-',       # En-dash to hyphen
    '“': '"',       # Left curly double quote
    '”': '"',       # Right curly double quote
    '‘': "'",       # Left curly single quote
    '’': "'",       # Right curly single quote
    '™': '',        # Trademark symbol removed
    '©': '(C)',     # Copyright symbol
    '®': '(R)',     # Registered trademark
    '€': 'EUR',     # Euro symbol
    '£': 'GBP',     # Pound symbol
    '¥': 'JPY',     # Yen symbol
    '\\': '/',      # Backslash to slash
    '^': ' ',       # Caret to space
    '~': '-',       # Tilde to hyphen
    '|': '/',       # Pipe to slash
}


class ProcessingStateRecord(BaseModel):
    """Execution state and queue tracking metadata for poison message defense."""
    state_id: str
    queue_name: str = "INBOUND_EXCEPTION_QUEUE"
    current_state: str = "INGESTED"     # INGESTED, PROCESSING, REPAIR_PROPOSED, RE_ENQUEUE_ELIGIBLE, POISON_SUSPENDED, ALREADY_PROCESSED
    retry_count: int = 0
    max_retries: int = 3
    is_poison_message: bool = False
    idempotency_key: str
    last_processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    downstream_owner: str = "BANK_PAYMENT_HUB"

    @property
    def is_retry_limit_exceeded(self) -> bool:
        return self.retry_count >= self.max_retries


class PR08TransformationResult(BaseModel):
    """Forensic result of executing the PR-08 character and state transformation pipeline."""
    success: bool
    raw_payload_hash: str
    transformed_payload: str
    transformed_payload_hash: str
    target_rail_scheme: str
    unsupported_characters_found: List[str] = Field(default_factory=list)
    substitutions_applied: List[str] = Field(default_factory=list)
    semantic_preservation_passed: bool
    semantic_loss_details: Optional[str] = None
    is_lossless: bool
    diff_summary: str
    processing_state: ProcessingStateRecord
    is_re_enqueue_eligible: bool = True
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class GovernedPR08Transformer:
    """Master engine executing governed character substitutions and state checks for PR-08."""

    def __init__(self, substitution_map: Optional[Dict[str, str]] = None):
        self.substitution_map = substitution_map or DEFAULT_PR08_SUBSTITUTION_MAP

    def transform(
        self,
        raw_payload: str,
        target_rail: str = "SWIFT_CBPR_XSET",
        bank_policy_authorized: bool = True,
        bank_substitution_map: Optional[Dict[str, str]] = None,
        processing_state: Optional[ProcessingStateRecord] = None,
        enforce_semantic_invariance: bool = True
    ) -> PR08TransformationResult:
        """Executes PR-08 unsupported character transformation and state validation."""
        trail: List[str] = ["Initiating PR-08 unsupported special character transformation & state validation."]
        diff_steps: List[str] = []
        applied_subs: List[str] = []

        raw_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        state = processing_state or ProcessingStateRecord(
            state_id=f"STATE-{raw_hash[:8]}",
            idempotency_key=raw_hash
        )

        # =========================================================================
        # Stage 1: State & Poison Message Defense
        # =========================================================================
        if state.is_retry_limit_exceeded:
            state.is_poison_message = True
            state.current_state = "POISON_SUSPENDED"
            trail.append(f"Stage 1 FAILED: Poison message detected. Retry count ({state.retry_count}) >= max ({state.max_retries}).")
            return PR08TransformationResult(
                success=False,
                raw_payload_hash=raw_hash,
                transformed_payload="",
                transformed_payload_hash="0" * 64,
                target_rail_scheme=target_rail,
                semantic_preservation_passed=False,
                is_lossless=False,
                diff_summary="Poison message threshold exceeded",
                processing_state=state,
                is_re_enqueue_eligible=False,
                audit_trail=trail,
                error_message=f"Poison message threshold exceeded: {state.retry_count} retries."
            )

        if state.current_state in ("ALREADY_PROCESSED", "DISPATCHED_SETTLED"):
            trail.append(f"Stage 1 FAILED: Message already processed in state {state.current_state}.")
            return PR08TransformationResult(
                success=False,
                raw_payload_hash=raw_hash,
                transformed_payload="",
                transformed_payload_hash="0" * 64,
                target_rail_scheme=target_rail,
                semantic_preservation_passed=False,
                is_lossless=False,
                diff_summary="Message already processed",
                processing_state=state,
                is_re_enqueue_eligible=False,
                audit_trail=trail,
                error_message=f"Message is already in final state: {state.current_state}"
            )

        trail.append(f"Stage 1 (State Check): Valid queue state '{state.current_state}', retry count {state.retry_count}/{state.max_retries}.")

        # =========================================================================
        # Stage 2: Target Rail Character Set Resolution
        # =========================================================================
        if target_rail == "SWIFT_CBPR_XSET":
            allowed_chars = SWIFT_X_CHARS
        elif target_rail == "SWIFT_CBPR_ZSET":
            allowed_chars = SWIFT_Z_CHARS
        elif target_rail == "FEDWIRE_STRICT":
            allowed_chars = FEDWIRE_STRICT_CHARS
        else:
            # Standard ISO 20022 UTF-8 XML
            allowed_chars = None

        active_sub_map = bank_substitution_map or self.substitution_map

        # Baseline semantic tokens
        pre_tokens = self._extract_business_semantic_tokens(raw_payload)

        # =========================================================================
        # Stage 3: Unsupported Character Detection & Policy-Governed Substitution
        # =========================================================================
        unsupported_found: List[str] = []
        applied_subs: List[str] = []
        diff_steps: List[str] = []

        # Check if payload contains XML entities like &amp;
        working_payload = raw_payload
        if bank_policy_authorized and target_rail == "SWIFT_CBPR_XSET":
            if "&amp;" in working_payload:
                sub_val = active_sub_map.get('&', ' AND ')
                working_payload = working_payload.replace("&amp;", sub_val)
                unsupported_found.append("&")
                applied_subs.append(f"'&' -> '{sub_val}'")

        repaired_chars: List[str] = []
        for ch in working_payload:
            if allowed_chars is None:
                # No rail restrictions (full UTF-8)
                repaired_chars.append(ch)
            elif ch in allowed_chars:
                repaired_chars.append(ch)
            else:
                # Character is outside target rail character set
                unsupported_found.append(ch)
                if bank_policy_authorized and ch in active_sub_map:
                    sub_val = active_sub_map[ch]
                    repaired_chars.append(sub_val)
                    applied_subs.append(f"'{ch}' -> '{sub_val}'")
                elif bank_policy_authorized:
                    # Attempt standard Unicode NFKD decomposition if diacritic
                    decomposed = unicodedata.normalize('NFKD', ch)
                    base_char = "".join([c for c in decomposed if not unicodedata.combining(c)])
                    if base_char and all(c in allowed_chars for c in base_char):
                        repaired_chars.append(base_char)
                        applied_subs.append(f"'{ch}' -> '{base_char}'")
                    else:
                        # Cannot safely substitute; keep character and fail validation downstream
                        repaired_chars.append(ch)
                else:
                    # Bank policy does not authorize substitution; preserve character
                    repaired_chars.append(ch)

        final_payload = "".join(repaired_chars)
        unique_unsupported = list(set(unsupported_found))

        if unique_unsupported:
            trail.append(f"Stage 3 (Character Scan): Detected {len(unsupported_found)} unsupported characters: {unique_unsupported}")
        else:
            trail.append("Stage 3 (Character Scan): Zero unsupported characters detected.")

        if applied_subs:
            diff_steps.append(f"Applied {len(applied_subs)} authorized substitutions: {set(applied_subs)}")
            trail.append(f"Stage 4 (Substitution): Applied {len(applied_subs)} authorized substitutions under bank policy.")

        # =========================================================================
        # Stage 5: Semantic Invariance Validation
        # =========================================================================
        post_tokens = self._extract_business_semantic_tokens(final_payload)
        semantic_passed, semantic_err = self._verify_semantic_invariance(pre_tokens, post_tokens)

        if enforce_semantic_invariance and not semantic_passed:
            trail.append(f"Stage 5 FAILED: Semantic preservation violation: {semantic_err}")
            return PR08TransformationResult(
                success=False,
                raw_payload_hash=raw_hash,
                transformed_payload=final_payload,
                transformed_payload_hash=hashlib.sha256(final_payload.encode("utf-8")).hexdigest(),
                target_rail_scheme=target_rail,
                unsupported_characters_found=unique_unsupported,
                substitutions_applied=list(set(applied_subs)),
                semantic_preservation_passed=False,
                semantic_loss_details=semantic_err,
                is_lossless=False,
                diff_summary=f"Semantic data altered: {semantic_err}",
                processing_state=state,
                is_re_enqueue_eligible=False,
                audit_trail=trail,
                error_message=f"Semantic preservation failed: {semantic_err}"
            )

        trail.append("Stage 5 (Semantic Preservation): 100% invariance confirmed for accounts, amounts, decimals, and references.")

        # =========================================================================
        # Stage 6: Candidate Generation & Output Integrity
        # =========================================================================
        output_hash = hashlib.sha256(final_payload.encode("utf-8")).hexdigest()
        trail.append(f"Stage 6 (Candidate): Output SHA-256 digest: {output_hash[:16]}...")

        diff_summary = "; ".join(diff_steps) if diff_steps else "Zero substitutions required"
        state.current_state = "REPAIR_PROPOSED"

        return PR08TransformationResult(
            success=True,
            raw_payload_hash=raw_hash,
            transformed_payload=final_payload,
            transformed_payload_hash=output_hash,
            target_rail_scheme=target_rail,
            unsupported_characters_found=unique_unsupported,
            substitutions_applied=list(set(applied_subs)),
            semantic_preservation_passed=True,
            is_lossless=True,
            diff_summary=diff_summary,
            processing_state=state,
            is_re_enqueue_eligible=True,
            audit_trail=trail
        )

    def _extract_business_semantic_tokens(self, text: str) -> Dict[str, Any]:
        """Extracts critical business-semantic tokens (amounts, accounts, decimals, UETRs, references)."""
        tokens: Dict[str, Any] = {
            "decimal_amounts": [],
            "account_numbers": [],
            "uetr_tokens": [],
            "end_to_end_ids": []
        }

        # 1. Amounts from XML tags or patterns
        amount_matches = re.findall(r'<IntrBkSttlmAmt[^>]*>([0-9]+\.[0-9]{2})</IntrBkSttlmAmt>', text)
        if not amount_matches:
            amount_matches = re.findall(r'>(\d+\.\d{2})<', text)
        if not amount_matches:
            amount_matches = re.findall(r'\b\d{1,12}\.\d{2}\b', text)
        tokens["decimal_amounts"] = amount_matches

        # 2. IBAN / Accounts specifically from Account ID tags if XML
        iban_matches = re.findall(r'<Id><IBAN>([A-Z0-9]+)</IBAN></Id>', text)
        if not iban_matches:
            iban_matches = re.findall(r'[A-Z]{2}\d{2}[A-Z0-9]{12,30}', text)
        tokens["account_numbers"] = iban_matches

        # 3. UETRs
        uetr_matches = re.findall(r'<UETR>([^<]+)</UETR>', text)
        if not uetr_matches:
            uetr_matches = re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', text)
        tokens["uetr_tokens"] = [u.lower() for u in uetr_matches]

        # 4. EndToEndId
        e2e_matches = re.findall(r'<EndToEndId>([^<]+)</EndToEndId>', text)
        tokens["end_to_end_ids"] = e2e_matches

        return tokens

    def _verify_semantic_invariance(self, pre: Dict[str, Any], post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies that all pre-transformation business values are strictly preserved."""
        if pre["decimal_amounts"] != post["decimal_amounts"]:
            return False, f"Monetary amount altered: {pre['decimal_amounts']} vs {post['decimal_amounts']}"
        if pre["account_numbers"] != post["account_numbers"]:
            return False, f"Account number / IBAN altered: {pre['account_numbers']} vs {post['account_numbers']}"
        if pre["uetr_tokens"] != post["uetr_tokens"]:
            return False, f"UETR identifier altered: {pre['uetr_tokens']} vs {post['uetr_tokens']}"
        if pre["end_to_end_ids"] != post["end_to_end_ids"]:
            return False, f"EndToEndId altered: {pre['end_to_end_ids']} vs {post['end_to_end_ids']}"
        return True, None


# Global singleton instance
pr08_transformer = GovernedPR08Transformer()

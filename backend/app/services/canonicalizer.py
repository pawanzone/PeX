"""Canonicalization Service: Ingests heterogeneous bank payloads and converts them to ISO 20022/SWIFT Canonical Entities."""
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid

from app.schemas.bank_events import RawBankEvent
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority
)
from app.core.tokenization import token_vault

def validate_iban_mod97(iban: str) -> bool:
    """Standard ISO 7064 MOD-97-10 check."""
    clean = iban.replace(" ", "").upper()
    if len(clean) < 4:
        return False
    rearranged = clean[4:] + clean[:4]
    num_str = ""
    for ch in rearranged:
        if ch.isdigit():
            num_str += ch
        elif ch.isalpha():
            num_str += str(ord(ch) - 55)
        else:
            return False
    try:
        return int(num_str) % 97 == 1
    except ValueError:
        return False

class CanonicalizerService:
    def canonicalize_bank_event(self, raw_event: RawBankEvent) -> Tuple[CanonicalPayment, CanonicalException]:
        p = raw_event.raw_payload
        bank_id = raw_event.source_bank_id
        
        if bank_id == "BANK_A":
            payment_ref = p.get("payment_reference") or f"REF-A-{uuid.uuid4().hex[:6].upper()}"
            uetr = p.get("uetr") or f"UETR-A-{uuid.uuid4().hex[:8]}"
            amount = float(p.get("amount", 42000.0))
            currency = p.get("currency", "USD")
            debtor_name = p.get("debtor_name", "Acme Global Holdings")
            debtor_acc = p.get("debtor_account", "US89CHAS12345678901234")
            creditor_name = p.get("creditor_name", "HarborView Supplier Ltd")
            creditor_iban = p.get("creditor_iban", "GB82WEST12345698765432")
            creditor_bic = p.get("creditor_bic", "WESTGB2L")
            error_code = p.get("error_code", "ERR_IBAN_MOD97")
            reason = p.get("error_message", "Beneficiary IBAN failed MOD-97 check validation against clearing directory.")
            rail = p.get("settlement_rail", "SWIFT_CBPR")
        elif bank_id == "BANK_B":
            header = p.get("header", {})
            body = p.get("body", {})
            payment_ref = header.get("trn") or f"TRN-B-{uuid.uuid4().hex[:6].upper()}"
            uetr = f"UETR-B-{uuid.uuid4().hex[:8]}"
            amount = float(body.get("amount", 250000.0))
            currency = body.get("ccy", "USD")
            debtor_name = body.get("ordering_customer", "Apex Global Treasury")
            debtor_acc = body.get("ordering_account", "US11APEX99887766554433")
            creditor_name = body.get("beneficiary_customer", "Nordhavn Components A/S")
            creditor_iban = body.get("beneficiary_iban", "DK50DABA30012345678901")
            creditor_bic = "DABADKKK"
            error_code = body.get("exception_code", "ERR_BENEFICIARY_DATA")
            reason = body.get("failure_reason", "Beneficiary account identifier failed validation against receiving bank profile.")
            rail = "SWIFT_CBPR+"
        elif bank_id == "BANK_C":
            camt = p.get("camt_code", "camt.056.001.08")
            uetr = p.get("uetr") or f"UETR-C-{uuid.uuid4().hex[:8]}"
            payment_ref = p.get("message_id") or f"MSG-C-{uuid.uuid4().hex[:6].upper()}"
            amt_info = p.get("amount", {})
            amount = float(amt_info.get("value", 380000.0))
            currency = amt_info.get("currency", "EUR")
            debtor_name = p.get("debtor", {}).get("name", "Euro Corp BV")
            debtor_acc = p.get("debtor", {}).get("account", "NL91ABNA0417164300")
            creditor_name = p.get("creditor", {}).get("name", "Al-Rashid Trading Gmbh")
            creditor_iban = p.get("creditor", {}).get("iban", "DE89370400440532013000")
            creditor_bic = "COBADEFF"
            error_code = p.get("return_reason", {}).get("code", "NARR_SANCTION_MATCH")
            reason = p.get("return_reason", {}).get("narrative", "Sanctions entity name similarity requires secondary screening.")
            rail = "ISO20022_pacs008"
        else:
            payment_ref = p.get("client_reference") or p.get("payment_ref") or f"REF-GEN-{uuid.uuid4().hex[:6].upper()}"
            uetr = p.get("uetr") or f"UETR-{uuid.uuid4().hex[:8]}"
            amount = float(p.get("amount", 42000.0))
            currency = p.get("currency", "USD")
            debtor_name = p.get("debtor_name", "Originating Debtor")
            debtor_acc = p.get("debtor_account", "ACC-DEBTOR-01")
            creditor_name = p.get("creditor_name", "Beneficiary Party")
            creditor_iban = p.get("creditor_iban", "GB82WEST12345698765432")
            creditor_bic = p.get("creditor_bic", "WESTGB2L")
            error_code = p.get("error_code", "ERR_GENERAL")
            reason = p.get("reason", "Payment processing exception.")
            rail = p.get("payment_rail", "SWIFT")

        profile = ExceptionProfile.INVALID_IBAN
        reason_upper = reason.upper()
        err_upper = error_code.upper()
        if "SANCTION" in reason_upper or "SANCTION" in err_upper:
            profile = ExceptionProfile.SANCTIONS_SUSPECTED
        elif "KYC" in reason_upper or "KYC" in err_upper:
            profile = ExceptionProfile.KYC_EXPIRED
        elif "DUPLICATE" in reason_upper or "DUPLICATE" in err_upper:
            profile = ExceptionProfile.DUPLICATE_PAYMENT
        elif "BIC" in reason_upper or "BIC" in err_upper or "ROUTING" in reason_upper:
            profile = ExceptionProfile.INVALID_BIC
        elif "RETURN" in reason_upper or "RECALL" in reason_upper:
            profile = ExceptionProfile.RETURNED_PAYMENT

        debtor_tok = token_vault.tokenize(debtor_name, "PARTY")
        creditor_tok = token_vault.tokenize(creditor_name, "PARTY")
        debtor_acc_tok = token_vault.tokenize(debtor_acc, "ACC")
        creditor_iban_tok = token_vault.tokenize(creditor_iban, "IBAN")

        debtor_party = CanonicalParty(
            party_id=f"PARTY-DEBTOR-{uuid.uuid4().hex[:4]}",
            party_name=debtor_name,
            party_type="DEBTOR",
            country="US" if currency == "USD" else "GB",
            token_ref=debtor_tok
        )
        debtor_account = CanonicalAccount(
            account_id=f"ACC-DEBTOR-{uuid.uuid4().hex[:4]}",
            account_number=debtor_acc,
            iban=debtor_acc if "IBAN" in debtor_acc or len(debtor_acc) > 15 else None,
            currency=currency,
            token_ref=debtor_acc_tok
        )
        creditor_party = CanonicalParty(
            party_id=f"PARTY-CREDITOR-{uuid.uuid4().hex[:4]}",
            party_name=creditor_name,
            party_type="CREDITOR",
            country="GB" if creditor_iban.startswith("GB") else ("DK" if creditor_iban.startswith("DK") else "DE"),
            token_ref=creditor_tok
        )
        creditor_account = CanonicalAccount(
            account_id=f"ACC-CREDITOR-{uuid.uuid4().hex[:4]}",
            account_number=creditor_iban[-8:],
            iban=creditor_iban,
            currency=currency,
            bank_bic=creditor_bic,
            token_ref=creditor_iban_tok
        )

        canonical_payment = CanonicalPayment(
            payment_id=f"PMT-{uuid.uuid4().hex[:8].upper()}",
            uetr=uetr,
            instruction_id=payment_ref,
            amount=amount,
            currency=currency,
            payment_rail=rail,
            debtor_party=debtor_party,
            debtor_account=debtor_account,
            creditor_party=creditor_party,
            creditor_account=creditor_account,
            source_bank_id=bank_id,
            raw_source_ref=raw_event.event_id
        )

        queue = "Repair"
        if profile in [ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.KYC_EXPIRED]:
            queue = "Compliance"
        elif profile in [ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.RETURNED_PAYMENT]:
            queue = "Investigation"

        severity = ExceptionSeverity.MEDIUM
        if amount >= 250000.0 or profile == ExceptionProfile.SANCTIONS_SUSPECTED:
            severity = ExceptionSeverity.HIGH
        if amount >= 1000000.0:
            severity = ExceptionSeverity.CRITICAL

        priority = ExceptionPriority.NORMAL
        if severity in [ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL]:
            priority = ExceptionPriority.HIGH
        if amount >= 1000000.0:
            priority = ExceptionPriority.CRITICAL

        case_id = f"PEX-{uuid.uuid4().hex[:6].upper()}"
        canonical_exception = CanonicalException(
            exception_id=f"EXC-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            profile=profile,
            error_code=error_code,
            reason=reason,
            severity=severity,
            priority=priority,
            sla_due_at=datetime.utcnow() + timedelta(hours=2),
            at_risk_amount=amount,
            assigned_queue=queue
        )

        return canonical_payment, canonical_exception

canonicalizer = CanonicalizerService()

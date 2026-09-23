"""Canonicalization Service: Ingests heterogeneous bank payloads and converts them to ISO 20022/SWIFT Canonical Entities."""
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import uuid

from app.schemas.bank_events import RawBankEvent
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority,
    ExceptionDomain, get_domain_for_profile
)
from app.core.tokenization import token_vault

import re

# Official ISO 13616 IBAN Registry Lengths (SWIFT Release 96+)
OFFICIAL_IBAN_COUNTRY_LENGTHS: Dict[str, int] = {
    "AL": 28, "AD": 24, "AT": 20, "AZ": 28, "BH": 22, "BY": 28, "BE": 16, "BA": 20,
    "BR": 29, "BG": 22, "CR": 22, "HR": 21, "CY": 28, "CZ": 24, "DK": 18, "DO": 28,
    "EE": 20, "FO": 18, "FI": 18, "FR": 27, "GE": 22, "DE": 22, "GI": 23, "GR": 27,
    "GL": 18, "GT": 28, "HU": 28, "IS": 26, "IE": 22, "IL": 23, "IT": 27, "JO": 30,
    "KZ": 20, "XK": 20, "KW": 30, "LV": 21, "LB": 28, "LI": 21, "LT": 20, "LU": 20,
    "MT": 31, "MR": 27, "MU": 30, "MD": 24, "MC": 27, "ME": 22, "NL": 18, "MK": 19,
    "NO": 15, "PK": 24, "PS": 29, "PL": 28, "PT": 25, "QA": 29, "RO": 24, "LC": 32,
    "SM": 27, "ST": 25, "SA": 24, "RS": 22, "SC": 31, "SK": 24, "SI": 19, "ES": 24,
    "SE": 24, "CH": 21, "TL": 23, "TN": 24, "TR": 26, "UA": 29, "AE": 23, "GB": 22,
    "VA": 22, "VG": 24
}

# Countries that do NOT issue IBANs (use domestic routing e.g. ABA, Zengin, BSB, etc.)
NON_IBAN_COUNTRIES = {"US", "JP", "SG", "AU", "CA", "NZ", "HK", "CN", "IN"}

# Official ISO 20022 External Purpose Codes (ExternalPurpose1Code)
VALID_ISO20022_PURPOSE_CODES = {
    "GDSV", "COMC", "MDCS", "TREA", "CORT", "SALA", "SUPP", "INTC",
    "DIVI", "PENS", "TAXS", "LOAN", "CHAR", "BONU", "COLL", "GOVT",
    "HEDG", "INSU", "INTE", "SECU", "SSBE", "TRAD", "UTIL", "VATX"
}

# Official ISO 20022 External Return Reason Codes (ExternalReturnReason1Code)
ISO20022_RETURN_REASON_CODES = {
    "AC01": "IncorrectAccountNumber",
    "AC04": "ClosedAccountNumber",
    "AC06": "BlockedAccount",
    "AG01": "TransactionForbidden",
    "AG02": "InvalidBankOperationCode",
    "RC01": "BankIdentifierIncorrect",
    "MS03": "NotSpecifiedReasonAgentGenerated",
    "MD07": "EndCustomerDeceased",
    "AM04": "InsufficientFunds",
    "DUPL": "DuplicatePayment"
}

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

def validate_iban_structure(iban: str) -> Tuple[bool, str]:
    """Comprehensive ISO 13616 & ISO 7064 structural and checksum validator."""
    clean = iban.replace(" ", "").upper()
    if len(clean) < 4:
        return False, "IBAN length too short (< 4 chars)"
    country_code = clean[:2]
    if country_code in NON_IBAN_COUNTRIES:
        return False, f"Country {country_code} does not issue IBANs (uses domestic account format)"
    if country_code not in OFFICIAL_IBAN_COUNTRY_LENGTHS:
        return False, f"Country {country_code} not recognized in ISO 13616 IBAN Registry"
    expected_length = OFFICIAL_IBAN_COUNTRY_LENGTHS[country_code]
    if len(clean) != expected_length:
        return False, f"Invalid IBAN length for {country_code}: expected {expected_length}, got {len(clean)}"
    
    # Specific country BBAN structural checks
    if country_code == "DE":
        # Germany: DE + 2 check digits + 8 BLZ (numeric) + 10 Account (numeric) = 22 numeric chars
        if not clean[2:].isdigit():
            return False, "German BBAN must contain only numeric digits (no letters allowed)"
    elif country_code == "GB":
        # UK: GB + 2 check digits + 4 bank alpha + 6 sort numeric + 8 account numeric = 22 chars
        if not clean[4:8].isalpha() or not clean[8:].isdigit():
            return False, "UK IBAN must follow GB2!n4!a6!n8!n format"
    
    if not validate_iban_mod97(clean):
        return False, "ISO 7064 MOD 97-10 checksum validation failed"
    return True, "Valid ISO 13616 IBAN"

def validate_fedwire_imad(imad: str) -> Tuple[bool, str]:
    """Validates Federal Reserve Fedwire IMAD (Input Message Accountability Data) strictly against FAIM 18-char standard."""
    clean = imad.strip().upper()
    if len(clean) != 18:
        return False, f"Fedwire IMAD must be strictly 18 characters, got {len(clean)}"
    # Pattern: 8 digits YYYYMMDD + 4 alphanumeric source ID + 6 digits sequence
    if not re.match(r"^[0-9]{8}[A-Z0-9]{4}[0-9]{6}$", clean):
        return False, "Fedwire IMAD must follow FAIM standard: YYYYMMDD (8 digits) + Source (4 alnum) + Sequence (6 digits)"
    return True, "Valid Fedwire FAIM IMAD"

def is_valid_iso20022_purpose_code(code: str) -> bool:
    """Validates 4-character payment purpose code against ISO 20022 ExternalPurpose1Code set."""
    if not code or len(code) != 4:
        return False
    return code.upper() in VALID_ISO20022_PURPOSE_CODES

class CanonicalizerService:
    def canonicalize_bank_event(
        self,
        raw_event: RawBankEvent,
        override_profile: Optional[ExceptionProfile] = None
    ) -> Tuple[CanonicalPayment, CanonicalException]:
        p = raw_event.raw_payload
        bank_id = raw_event.source_bank_id
        
        if bank_id == "BANK_A":
            payment_ref = p.get("payment_reference") or f"REF-A-{uuid.uuid4().hex[:6].upper()}"
            uetr = p.get("uetr") or f"UETR-A-{uuid.uuid4().hex[:8]}"
            amount = float(p.get("amount", 42000.0))
            currency = p.get("currency", "USD")
            debtor_name = p.get("debtor_name", "Acme Global Holdings")
            debtor_acc = p.get("debtor_account", "021000021-12345678901234")
            creditor_name = p.get("creditor_name", "HarborView Supplier Ltd")
            creditor_iban = p.get("creditor_iban", "GB82WEST12345698765432")
            creditor_bic = p.get("creditor_bic", "WESTGB2L")
            error_code = p.get("error_code", "ERR_IBAN_MOD97")
            reason = p.get("error_message", "Beneficiary IBAN failed MOD-97 check validation against clearing directory.")
            rail = p.get("settlement_rail", "SWIFT_CBPR")
        elif bank_id == "BANK_B":
            header = p.get("header", {})
            body = p.get("body", {})
            payment_ref = header.get("trn") or p.get("payment_reference") or p.get("payment_ref") or f"TRN-B-{uuid.uuid4().hex[:6].upper()}"
            uetr = p.get("uetr") or f"UETR-B-{uuid.uuid4().hex[:8]}"
            amount = float(body.get("amount") if body.get("amount") is not None else p.get("amount", 250000.0))
            currency = body.get("ccy") or p.get("currency", "USD")
            debtor_name = body.get("ordering_customer") or p.get("debtor_name", "Apex Global Treasury")
            debtor_acc = body.get("ordering_account") or p.get("debtor_account", "021000021-99887766554433")
            creditor_name = body.get("beneficiary_customer") or p.get("creditor_name", "Nordhavn Components A/S")
            creditor_iban = body.get("beneficiary_iban") or p.get("creditor_iban", "DK50DABA30012345678901")
            creditor_bic = p.get("creditor_bic", "DABADKKK")
            error_code = body.get("exception_code") or p.get("error_code", "ERR_BENEFICIARY_DATA")
            reason = body.get("failure_reason") or p.get("error_message", "Beneficiary account identifier failed validation against receiving bank profile.")
            rail = p.get("settlement_rail", "SWIFT_CBPR+")
        elif bank_id == "BANK_C":
            camt = p.get("camt_code", "camt.056.001.08")
            uetr = p.get("uetr") or f"UETR-C-{uuid.uuid4().hex[:8]}"
            payment_ref = p.get("message_id") or p.get("payment_reference") or p.get("payment_ref") or f"MSG-C-{uuid.uuid4().hex[:6].upper()}"
            amt_info = p.get("amount", {})
            if isinstance(amt_info, dict):
                amount = float(amt_info.get("value", 380000.0))
                currency = amt_info.get("currency", p.get("currency", "EUR"))
            else:
                amount = float(amt_info)
                currency = p.get("currency", "EUR")
            debtor_dict = p.get("debtor", {})
            debtor_name = debtor_dict.get("name") if isinstance(debtor_dict, dict) else p.get("debtor_name", "Euro Corp BV")
            debtor_acc = debtor_dict.get("account") if isinstance(debtor_dict, dict) else p.get("debtor_account", "NL91ABNA0417164300")
            creditor_dict = p.get("creditor", {})
            creditor_name = creditor_dict.get("name") if isinstance(creditor_dict, dict) else p.get("creditor_name", "Al-Rashid Trading Gmbh")
            creditor_iban = creditor_dict.get("iban") if isinstance(creditor_dict, dict) else p.get("creditor_iban", "DE89370400440532013000")
            creditor_bic = p.get("creditor_bic", "COBADEFF")
            return_reason = p.get("return_reason", {})
            if isinstance(return_reason, dict):
                error_code = return_reason.get("code", "NARR_SANCTION_MATCH")
                reason = return_reason.get("narrative", "Sanctions entity name similarity requires secondary screening.")
            else:
                error_code = p.get("error_code", "NARR_SANCTION_MATCH")
                reason = p.get("error_message", "Sanctions entity name similarity requires secondary screening.")
            rail = p.get("settlement_rail", "ISO20022_pacs008")
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

        if override_profile:
            profile = override_profile
        else:
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
        domain = get_domain_for_profile(profile)
        canonical_exception = CanonicalException(
            exception_id=f"EXC-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            profile=profile,
            domain=domain,
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

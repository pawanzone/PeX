with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\tests\test_canonicalization.py", "w", encoding="utf-8") as f:
    f.write('''"""Tests for Multi-Bank Ingestion and Canonicalization."""
import pytest
from app.schemas.bank_events import RawBankEvent
from app.services.canonicalizer import canonicalizer, validate_iban_mod97
from app.schemas.canonical import ExceptionProfile

def test_iban_mod97_validator():
    # Valid ISO 7064 MOD-97 IBANs evaluate to True (% 97 == 1)
    assert validate_iban_mod97("GB82WEST12345698765432") is True
    assert validate_iban_mod97("GB29NWBK60161331926819") is True
    # Corrupted / invalid check digit evaluates to False
    assert validate_iban_mod97("GB82WEST12345698765431") is False
    assert validate_iban_mod97("GB00WEST12345698765432") is False

def test_bank_a_canonicalization():
    event = RawBankEvent(
        event_id="EVT-A-01",
        source_bank_id="BANK_A",
        event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": "REF-A-99",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary IBAN failed MOD-97 check validation",
            "amount": 42000.0,
            "currency": "USD",
            "debtor_name": "Global Corp",
            "debtor_account": "US12345",
            "creditor_name": "UK Supplier",
            "creditor_iban": "GB82WEST12345698765431"
        }
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    assert pmt.amount == 42000.0
    assert pmt.currency == "USD"
    assert exc.profile == ExceptionProfile.INVALID_IBAN
    assert exc.assigned_queue == "Repair"

def test_bank_c_sanctions_canonicalization():
    event = RawBankEvent(
        event_id="EVT-C-01",
        source_bank_id="BANK_C",
        event_type="SANCTIONS_ALERT",
        raw_payload={
            "message_id": "MSG-C-99",
            "format": "ISO20022_WRAPPER",
            "amount": {"value": 380000.0, "currency": "EUR"},
            "debtor": {"name": "Euro Corp", "account": "NL91ABNA0417164300"},
            "creditor": {"name": "Al-Rashid Trading", "iban": "DE89370400440532013000"},
            "return_reason": {"code": "SANCTION_HIT", "narrative": "Sanctions match suspected"}
        }
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    assert pmt.amount == 380000.0
    assert exc.profile == ExceptionProfile.SANCTIONS_SUSPECTED
    assert exc.assigned_queue == "Compliance"
''')

print("Updated tests/test_canonicalization.py")

"""Tests for Pydantic v2 Canonical Schemas and Contracts."""
import pytest
from app.schemas.canonical import (
    CanonicalPayment, CanonicalParty, CanonicalAccount, CanonicalException,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority
)
from app.schemas.bank_events import RawBankEvent, BankAEventPayload

def test_canonical_payment_contract():
    debtor = CanonicalParty(
        party_id="P-01", party_name="Acme Corp", party_type="DEBTOR", country="US"
    )
    debtor_acc = CanonicalAccount(
        account_id="ACC-01", account_number="12345678", currency="USD"
    )
    creditor = CanonicalParty(
        party_id="P-02", party_name="Beneficiary Ltd", party_type="CREDITOR", country="GB"
    )
    creditor_acc = CanonicalAccount(
        account_id="ACC-02", iban="GB82WEST12345698765432", currency="USD"
    )
    pmt = CanonicalPayment(
        payment_id="PMT-100",
        uetr="UETR-100",
        instruction_id="INS-100",
        amount=42000.0,
        currency="USD",
        payment_rail="SWIFT_CBPR+",
        debtor_party=debtor,
        debtor_account=debtor_acc,
        creditor_party=creditor,
        creditor_account=creditor_acc,
        source_bank_id="BANK_A"
    )
    assert pmt.amount == 42000.0
    assert pmt.currency == "USD"
    assert pmt.debtor_party.country == "US"

def test_raw_bank_event_validation():
    event = RawBankEvent(
        event_id="EVT-001",
        source_bank_id="BANK_A",
        event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": "REF-001",
            "error_code": "ERR_IBAN",
            "error_message": "Invalid Checksum",
            "amount": 50000.0,
            "currency": "USD",
            "debtor_name": "Test Debtor",
            "debtor_account": "111111",
            "creditor_name": "Test Creditor",
            "creditor_iban": "GB82WEST12345698765432"
        }
    )
    assert event.event_id == "EVT-001"
    assert event.source_bank_id == "BANK_A"

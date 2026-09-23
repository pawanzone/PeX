"""Tests for PII Tokenization Vault & Privacy Boundary."""
import pytest
from app.core.tokenization import token_vault
from app.services.context_builder import context_builder
from app.schemas.canonical import CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount, ExceptionProfile, ExceptionSeverity, ExceptionPriority

def test_token_vault_masking():
    token = token_vault.tokenize("HarborView Supplier Ltd", "PARTY")
    assert token.startswith("TOK-PARTY-")
    
    masked = token_vault.mask_identifier("GB82WEST12345698765432")
    assert masked.startswith("GB82")
    assert masked.endswith("5432")
    assert "****" in masked

def test_zero_pii_in_ai_context():
    debtor = CanonicalParty(party_id="P1", party_name="John Doe Private", party_type="DEBTOR", country="US")
    debtor_acc = CanonicalAccount(account_id="A1", account_number="12345678901234", currency="USD")
    creditor = CanonicalParty(party_id="P2", party_name="Jane Smith Secret", party_type="CREDITOR", country="GB")
    creditor_acc = CanonicalAccount(account_id="A2", iban="GB82WEST12345698765432", currency="USD")
    
    pmt = CanonicalPayment(
        payment_id="PMT-1", uetr="UETR-1", instruction_id="INS-1", amount=1000.0, currency="USD",
        payment_rail="SWIFT", debtor_party=debtor, debtor_account=debtor_acc,
        creditor_party=creditor, creditor_account=creditor_acc, source_bank_id="BANK_A"
    )
    exc = CanonicalException(
        exception_id="EXC-1", case_id="CASE-1", profile=ExceptionProfile.INVALID_IBAN,
        error_code="ERR", reason="Test", severity=ExceptionSeverity.LOW,
        priority=ExceptionPriority.NORMAL, sla_due_at="2026-08-24T12:00:00",
        at_risk_amount=1000.0, assigned_queue="Repair"
    )
    
    ctx = context_builder.build_investigation_context(
        payment=pmt, exception=exc, evidence_items=[], policies=[], historical_cases=[]
    )
    
    ctx_dict = ctx.model_dump() if hasattr(ctx, "model_dump") else ctx.dict()
    ctx_str = str(ctx_dict)
    
    # Assert raw PII names are NOT present in AI context
    assert "John Doe Private" not in ctx_str
    assert "Jane Smith Secret" not in ctx_str
    assert "12345678901234" not in ctx_str
    # Assert Token IDs are present
    assert "TOK-PARTY-" in ctx_str

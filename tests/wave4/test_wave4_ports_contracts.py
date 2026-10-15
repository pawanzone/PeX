"""Tests for Wave 4 SPI Abstract Ports & Reference In-Memory Adapters.

Validates:
- KycMasterPort & InMemoryKycMasterAdapter
- CorporateMandatePort & InMemoryCorporateMandateAdapter
- TransitTrackerPort & InMemoryTransitTrackerAdapter
"""
import pytest
from app.ports.kyc_master_port import KycMasterPort
from app.ports.corporate_mandate_port import CorporateMandatePort
from app.ports.transit_tracker_port import TransitTrackerPort

from app.adapters.reference.reference_kyc_master_adapter import InMemoryKycMasterAdapter
from app.adapters.reference.reference_corporate_mandate_adapter import InMemoryCorporateMandateAdapter
from app.adapters.reference.reference_transit_tracker_adapter import InMemoryTransitTrackerAdapter


def test_kyc_master_adapter_contract():
    adapter = InMemoryKycMasterAdapter()
    assert isinstance(adapter, KycMasterPort)

    rec = adapter.get_kyc_record("CLI-CORP-001")
    assert rec is not None
    assert rec.client_id == "CLI-CORP-001"
    assert rec.refresh_in_progress is True

    standing = adapter.get_corporate_standing("CLI-CORP-001")
    assert standing is not None
    assert standing.tier_rating == "TIER_1_MULTINATIONAL"
    assert standing.has_active_sar_or_regulatory_query is False

    policy = adapter.get_waiver_policy()
    assert policy.allow_provisional_waiver is True
    assert policy.max_waiver_amount == 50000.0

    waiver = adapter.generate_provisional_waiver("CLI-CORP-001", 30)
    assert waiver is not None
    assert waiver.waiver_duration_days == 30
    assert waiver.execution_owner == "BANK"


def test_corporate_mandate_adapter_contract():
    adapter = InMemoryCorporateMandateAdapter()
    assert isinstance(adapter, CorporateMandatePort)

    mandate = adapter.get_mandate_record("ACCT-CORP-USD-001")
    assert mandate is not None
    assert mandate.debtor_account == "ACCT-CORP-USD-001"
    assert "CLASS_A" in mandate.allowed_signer_classes

    signer = adapter.get_secondary_signatory("ACCT-CORP-USD-001")
    assert signer is not None
    assert signer.signature_status == "APPROVED"
    assert signer.mfa_verified is True

    callback = adapter.get_portal_callback("ACCT-CORP-USD-001")
    assert callback is not None
    assert callback.callback_status == "VERIFIED"

    clearance = adapter.generate_dual_auth_clearance("MAND-APEX-01", "SIG-PRIMARY-01", "SIG-CFO-001")
    assert clearance is not None
    assert clearance.authorization_status == "DUAL_AUTHORIZATION_VERIFIED"
    assert clearance.execution_owner == "BANK"


def test_transit_tracker_adapter_contract():
    adapter = InMemoryTransitTrackerAdapter()
    assert isinstance(adapter, TransitTrackerPort)

    hop = adapter.get_tracker_hop("UETR-ST06-SUFF")
    assert hop is not None
    assert hop.intermediary_bic == "DEUTDEDDXXX"
    assert hop.hop_status == "HELD_AT_INTERMEDIARY"
    assert hop.hold_duration_minutes == 180.0

    debit = adapter.get_debit_confirmation("UETR-ST06-SUFF")
    assert debit is not None
    assert debit.is_confirmed is True
    assert debit.amount == 125000.0

    policy = adapter.get_inquiry_policy()
    assert policy.min_hold_minutes_for_inquiry == 120.0
    assert policy.inquiry_message_type == "CAMT_056"

    candidate = adapter.generate_investigation_candidate("UETR-ST06-SUFF", "DEUTDEDDXXX", "CAMT_056")
    assert candidate is not None
    assert candidate.status == "DISPATCH_CAMT_056_INTERMEDIARY_INQUIRY"
    assert candidate.autonomous_stp_prohibited is True
    assert candidate.execution_owner == "BANK"

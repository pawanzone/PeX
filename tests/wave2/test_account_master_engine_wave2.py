"""Unit Tests for AccountMasterEngine Wave 2 Extensions (ST-02, ST-03).

Verifies:
1. ST-02 Closed Account determination, Governed Return compilation (AC04), and strict replacement account prohibition.
2. ST-02 Corporate Rollover Mandate handling under W2-BPD-02.
3. ST-03 Beneficiary Account Frozen credit restriction scope (Post No Credits / PNC vs Debit Only).
4. ST-03 Statutory sanctions block strict boundary separation (Divert to CO-01).
5. ST-03 Legal Suspense Escrow booking under W2-BPD-03.
"""
import pytest
from app.services.engines.account_master_engine import AccountMasterEngine
from app.adapters.reference.reference_account_master_adapter import InMemoryAccountMasterAdapter
from app.adapters.reference.reference_legal_registry_adapter import InMemoryLegalRegistryAdapter
from app.schemas.contracts.policy_schemas import W2PolicyThresholds
from app.schemas.contracts.wave1_schemas import AccountMasterRecord
from app.schemas.contracts.wave2_schemas import (
    AccountClosedRecord,
    AccountRestrictionScope,
    AccountRestrictionType,
)
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    acct_adapter = InMemoryAccountMasterAdapter()
    legal_adapter = InMemoryLegalRegistryAdapter()
    # Register closed account
    acct_adapter.register_account(
        AccountMasterRecord(
            account_number="99887700",
            account_title="PACIFIC RIM TRADING CORP",
            account_status="CLOSED",
            currency="USD",
            bank_id_or_bic="CHASUS33XXX",
            country="US"
        )
    )
    return AccountMasterEngine(account_port=acct_adapter, legal_port=legal_adapter)


class TestAccountMasterEngineST02:
    """Unit tests for ST-02: Account Closed."""

    def test_st02_happy_path_governed_return(self, engine):
        policy = W2PolicyThresholds(allow_closed_account_auto_return=True, max_closed_account_auto_return_amount=100000.0)
        status, uniq, cand, diffs, err = engine.resolve_st02_account_closed(
            account_number="99887700",
            uetr="UETR-ST02-001",
            payment_id="PMT-ST02-001",
            amount=12000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["return_reason_code"] == "AC04"
        assert "RETURN" in cand.derivation_method

    def test_st02_strict_replacement_account_prohibition(self, engine):
        """AI/PeX cannot synthesize or substitute replacement accounts autonomously."""
        status, uniq, cand, diffs, err = engine.resolve_st02_account_closed(
            account_number="99887700",
            uetr="UETR-ST02-ADV",
            payment_id="PMT-ST02-ADV",
            amount=12000.0,
            currency="USD",
            evidence_context={"autonomous_replacement_attempt": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "prohibited" in err.lower()

    def test_st02_contradictory_status_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_st02_account_closed(
            account_number="99887700",
            uetr="UETR-ST02-CONTR",
            payment_id="PMT-ST02-CONTR",
            amount=12000.0,
            currency="USD",
            evidence_context={"contradictory_account_status": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_AMBIGUOUS
        assert "contradictory" in err.lower()

    def test_st02_corporate_rollover_with_mandate_allowed(self, engine):
        policy = W2PolicyThresholds(allow_mandate_rollover=True, require_dual_auth_for_rollover=False)
        status, uniq, cand, diffs, err = engine.resolve_st02_account_closed(
            account_number="99887700",
            uetr="UETR-ST02-ROLL",
            payment_id="PMT-ST02-ROLL",
            amount=12000.0,
            currency="USD",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert cand.repaired_structured["action"] == "ROLLOVER_TO_SUCCESSOR_ACCOUNT"
        assert cand.repaired_structured["successor_account_number"] == "99887766"


class TestAccountMasterEngineST03:
    """Unit tests for ST-03: Beneficiary Account Frozen."""

    def test_st03_happy_path_governed_return_pnc(self, engine):
        policy = W2PolicyThresholds(allow_frozen_account_auto_return=True, max_frozen_account_auto_return_amount=100000.0)
        status, uniq, cand, diffs, err = engine.resolve_st03_account_frozen(
            account_number="33445566",
            uetr="UETR-ST03-001",
            payment_id="PMT-ST03-001",
            amount=25000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["return_reason_code"] == "PNC"

    def test_st03_debit_only_restriction_permits_credits(self, engine):
        """If restriction is DEBIT_ONLY, credit postings are permitted, so ST-03 does not block."""
        status, uniq, cand, diffs, err = engine.resolve_st03_account_frozen(
            account_number="55667788", # DEBIT_ONLY account
            uetr="UETR-ST03-DEBITONLY",
            payment_id="PMT-ST03-DEBITONLY",
            amount=5000.0,
            currency="USD"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert "permits credit" in err.lower()

    def test_st03_statutory_sanctions_diverts_to_co01(self, engine):
        """Statutory sanctions must not be returned; must divert to CO-01."""
        status, uniq, cand, diffs, err = engine.resolve_st03_account_frozen(
            account_number="77889900", # Sanctioned Petroleum Assets
            uetr="UETR-ST03-SANCTIONS",
            payment_id="PMT-ST03-SANCTIONS",
            amount=50000.0,
            currency="USD"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert "co-01" in err.lower()

    def test_st03_legal_suspense_escrow_booking(self, engine):
        policy = W2PolicyThresholds(allow_legal_suspense_booking=True)
        status, uniq, cand, diffs, err = engine.resolve_st03_account_frozen(
            account_number="33445566",
            uetr="UETR-ST03-SUSP",
            payment_id="PMT-ST03-SUSP",
            amount=25000.0,
            currency="USD",
            policy_thresholds=policy,
            evidence_context={"requested_disposition": "LEGAL_SUSPENSE_ESCROW"}
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert cand.repaired_structured["suspense_gl_account"] == "GL-2180-LEGAL-SUSPENSE-ESCROW"
        assert "SUSPENSE" in cand.derivation_method

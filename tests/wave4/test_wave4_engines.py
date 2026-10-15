"""Tests for Wave 4 Resolution Engine (Wave4ResolutionEngine).

Validates resolution logic, guardrails, policy thresholds, and fail-closed behaviors for:
- TR-01: KYC Expired (SOP-302 Provisional Waiver Evaluation)
- TR-05: Authorization Missing (Corporate Mandate & Secondary Digital Signatory)
- ST-06: Funds Trapped at Correspondent (SWIFT gpi Transit Break & camt.056 Inquiry)
"""
import pytest
from app.services.engines.wave4_resolution_engine import Wave4ResolutionEngine
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness
from app.schemas.contracts.policy_schemas import W4PolicyThresholds


@pytest.fixture
def engine():
    return Wave4ResolutionEngine()


# ==============================================================================
# TR-01: KYC EXPIRED TESTS
# ==============================================================================

def test_tr01_kyc_expired_positive(engine):
    """Positive: Tier 1 corporate, refresh in progress, clean history -> provisional waiver."""
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-CORP-001",
        amount=5000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_PROVISIONAL_KYC_WAIVER"
    assert cand.repaired_structured["provisional_status"] == "WAIVER_ACTIVE_30_DAYS"
    assert cand.repaired_structured["execution_owner"] == "BANK"
    assert err is None


def test_tr01_kyc_expired_unknown_client_fails_closed(engine):
    """Negative: Unknown client ID with no KYC record fails closed."""
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-UNKNOWN-999",
        amount=5000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert err is not None
    assert "Missing KYC master record" in err


def test_tr01_kyc_expired_active_sar_fails_closed(engine):
    """Negative: Client with active SAR flag fails closed under compliance guardrails."""
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-DISTRESSED-02",
        amount=5000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Active SAR flag" in err


def test_tr01_kyc_expired_high_risk_corridor_fails_closed(engine):
    """Negative: High-risk corridor prohibits provisional waiver."""
    ctx = {
        "customer_kyc_record": {
            "client_id": "CLI-HIGH-RISK-01",
            "refresh_in_progress": True,
            "dispute_free_months": 36,
        },
        "corporate_standing_record": {
            "client_id": "CLI-HIGH-RISK-01",
            "tier_rating": "TIER_1_MULTINATIONAL",
            "has_active_sar_or_regulatory_query": False,
            "clearing_corridor_risk": "HIGH",
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-HIGH-RISK-01",
        amount=5000.0,
        currency="USD",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "High-risk corridor" in err


def test_tr01_kyc_expired_no_refresh_fails_closed(engine):
    """Negative: Documentation refresh not initiated fails closed."""
    ctx = {
        "customer_kyc_record": {
            "client_id": "CLI-NO-REFRESH",
            "refresh_in_progress": False,
            "dispute_free_months": 36,
        },
        "corporate_standing_record": {
            "client_id": "CLI-NO-REFRESH",
            "has_active_sar_or_regulatory_query": False,
            "clearing_corridor_risk": "LOW",
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-NO-REFRESH",
        amount=5000.0,
        currency="USD",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Documentation refresh not in progress" in err


def test_tr01_kyc_expired_amount_exceeds_waiver_threshold(engine):
    """Negative: Amount exceeding policy waiver maximum ($50k) fails closed."""
    status, uniq, cand, diff_log, err = engine.resolve_tr01_kyc_expired(
        client_id="CLI-CORP-001",
        amount=75000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "exceeds max provisional KYC waiver threshold" in err


# ==============================================================================
# TR-05: AUTHORIZATION MISSING TESTS
# ==============================================================================

def test_tr05_authorization_missing_positive(engine):
    """Positive: Mandate on file, Class A signatory approved with MFA, callback verified."""
    status, uniq, cand, diff_log, err = engine.resolve_tr05_authorization_missing(
        debtor_account="ACCT-CORP-USD-001",
        amount=7500.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_CORPORATE_DUAL_AUTH_VERIFICATION"
    assert cand.repaired_structured["authorization_status"] == "DUAL_AUTHORIZATION_VERIFIED"
    assert cand.repaired_structured["execution_owner"] == "BANK"
    assert err is None


def test_tr05_authorization_missing_unknown_account_fails_closed(engine):
    """Negative: Unknown debtor account with no mandate fails closed."""
    status, uniq, cand, diff_log, err = engine.resolve_tr05_authorization_missing(
        debtor_account="ACCT-UNKNOWN-999",
        amount=7500.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Missing corporate mandate" in err


def test_tr05_authorization_missing_signature_pending_fails_closed(engine):
    """Negative: Secondary signature still pending in portal queue fails closed."""
    status, uniq, cand, diff_log, err = engine.resolve_tr05_authorization_missing(
        debtor_account="ACCT-UNAPPROVED-USD-002",
        amount=7500.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Secondary signature is PENDING" in err


def test_tr05_authorization_missing_unauthorized_signer_class(engine):
    """Negative: Signatory class unauthorized under mandate fails closed."""
    ctx = {
        "corporate_mandate_record": {
            "mandate_id": "MAND-STRICT-01",
            "debtor_account": "ACCT-STRICT-01",
            "allowed_signer_classes": ["CLASS_A"],
        },
        "secondary_signatory_record": {
            "signatory_id": "SIG-CLASS-C",
            "signer_class": "CLASS_C",
            "signature_status": "APPROVED",
            "mfa_verified": True,
        },
        "portal_callback_record": {
            "debtor_account": "ACCT-STRICT-01",
            "callback_status": "VERIFIED",
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_tr05_authorization_missing(
        debtor_account="ACCT-STRICT-01",
        amount=7500.0,
        currency="USD",
        secondary_signatory_id="SIG-CLASS-C",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "unauthorized" in err.lower()


def test_tr05_authorization_missing_portal_callback_unreachable(engine):
    """Negative: Out-of-band portal callback failure fails closed."""
    ctx = {
        "corporate_mandate_record": {
            "mandate_id": "MAND-CB-FAIL",
            "debtor_account": "ACCT-CB-FAIL",
            "allowed_signer_classes": ["CLASS_A"],
        },
        "secondary_signatory_record": {
            "signatory_id": "SIG-CB-FAIL",
            "signer_class": "CLASS_A",
            "signature_status": "APPROVED",
            "mfa_verified": True,
        },
        "portal_callback_record": {
            "debtor_account": "ACCT-CB-FAIL",
            "callback_status": "UNREACHABLE",
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_tr05_authorization_missing(
        debtor_account="ACCT-CB-FAIL",
        amount=7500.0,
        currency="USD",
        secondary_signatory_id="SIG-CB-FAIL",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Portal callback verification failed" in err


# ==============================================================================
# ST-06: FUNDS TRAPPED AT CORRESPONDENT TESTS
# ==============================================================================

def test_st06_funds_trapped_positive(engine):
    """Positive: Confirmed debit, held at intermediary >= 120m -> camt.056 inquiry dossier."""
    status, uniq, cand, diff_log, err = engine.resolve_st06_funds_trapped(
        uetr="UETR-ST06-SUFF",
        amount=125000.0,
        currency="EUR",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_F_INTERMEDIARY_INQUIRY_DOSSIER"
    assert cand.repaired_structured["status"] == "DISPATCH_CAMT_056_INTERMEDIARY_INQUIRY"
    assert cand.repaired_structured["autonomous_stp_prohibited"] is True
    assert cand.repaired_structured["execution_owner"] == "BANK"
    assert err is None


def test_st06_funds_trapped_missing_telemetry_fails_closed(engine):
    """Negative: Missing SWIFT gpi tracker hop telemetry fails closed."""
    status, uniq, cand, diff_log, err = engine.resolve_st06_funds_trapped(
        uetr="UETR-NON-EXISTENT",
        amount=125000.0,
        currency="EUR",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Missing authoritative tracker telemetry" in err


def test_st06_funds_trapped_unconfirmed_debit_fails_closed(engine):
    """Negative: Debit not confirmed from debtor account fails closed."""
    ctx = {
        "tracker_hop_record": {
            "uetr": "UETR-NO-DEBIT",
            "intermediary_bic": "DEUTDEDDXXX",
            "hold_duration_minutes": 180.0,
            "hop_status": "HELD_AT_INTERMEDIARY",
        },
        "debit_confirmation_record": {
            "debit_reference": "DBT-FAIL",
            "debtor_account": "ACCT-ST06",
            "amount": 125000.0,
            "currency": "EUR",
            "is_confirmed": False,
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_st06_funds_trapped(
        uetr="UETR-NO-DEBIT",
        amount=125000.0,
        currency="EUR",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Unconfirmed debit" in err


def test_st06_funds_trapped_hold_below_threshold_fails_closed(engine):
    """Negative: Hold duration below inquiry policy threshold (<120m) fails closed."""
    ctx = {
        "tracker_hop_record": {
            "uetr": "UETR-SHORT-HOLD",
            "intermediary_bic": "DEUTDEDDXXX",
            "hold_duration_minutes": 45.0,  # Below 120m
            "hop_status": "HELD_AT_INTERMEDIARY",
        },
        "debit_confirmation_record": {
            "debit_reference": "DBT-OK",
            "debtor_account": "ACCT-ST06",
            "amount": 125000.0,
            "currency": "EUR",
            "is_confirmed": True,
        },
    }
    status, uniq, cand, diff_log, err = engine.resolve_st06_funds_trapped(
        uetr="UETR-SHORT-HOLD",
        amount=125000.0,
        currency="EUR",
        evidence_context=ctx,
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None
    assert "Hold duration below inquiry threshold" in err


def test_st06_zero_auto_stp_invariant(engine):
    """Invariant: ST-06 candidate package must strictly prohibit autonomous STP."""
    status, uniq, cand, diff_log, err = engine.resolve_st06_funds_trapped(
        uetr="UETR-ST06-SUFF",
        amount=125000.0,
        currency="EUR",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert cand.repaired_structured["autonomous_stp_prohibited"] is True
    assert cand.repaired_structured["execution_owner"] == "BANK"

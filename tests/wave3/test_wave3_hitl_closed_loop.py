"""Tests for Wave 3 Closed-Loop Human-in-the-Loop (HITL) Adjudication & Approval Workflows."""
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo
from app.schemas.contracts.wave3_schemas import CreditDecisionRecord


@pytest.fixture
def harness():
    return E2EExecutionHarness()


def test_tr06_limit_waiver_hitl_loop(harness):
    """Verifies that high-value limit breach generates an operational waiver dossier for HITL."""
    inp = CanonicalE2EInput(
        exception_id="HITL-TR06-01",
        profile_id="TR-06",
        domain="CLIENT_TREASURY",
        error_code="ERR_LIMIT_BREACH",
        error_message="High-value limit breach requiring human waiver",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-HITL-01",
            uetr="UETR-HITL-01",
            amount=300000.0,  # Exceeds dual-auth threshold
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="Apex Corp",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="CHASUS33XXX",
        ),
        bank_supplied_evidence={
            "limit_id": "LIM-BREACHED-01",
            "client_id": "CLI-CORP-001",
            "limit_utilization_record": {
                "limit_id": "LIM-BREACHED-01",
                "limit_type": "DAILY_ACCOUNT_LIMIT",
                "limit_cap": 500000.0,
                "current_utilization": 490000.0,
                "currency": "USD",
                "is_breached": False,
                "is_authoritative": True,
            },
            "client_limit_agreement": {
                "client_id": "CLI-CORP-001",
                "account_number": "ACCT-CORP-USD-001",
            },
        },
    )
    out = harness.process_input(inp)
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.resolution_recommendation is not None
    assert "dossier_id" in out.resolution_recommendation or "pacing_schedule" in out.resolution_recommendation


def test_tr08_credit_adjudication_hitl_loop(harness):
    """Verifies that TR-08 produces governed CreditRiskDossier with mandatory Senior Credit Officer dual-auth."""
    inp = CanonicalE2EInput(
        exception_id="HITL-TR08-01",
        profile_id="TR-08",
        domain="CLIENT_TREASURY",
        error_code="ERR_CREDIT_EXPOSURE_BREACH",
        error_message="Borrower credit facility breach",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-HITL-02",
            uetr="UETR-HITL-02",
            amount=800000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="CPTY-CORP-ALPHA",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="ALPHUS33XXX",
        ),
        bank_supplied_evidence={
            "counterparty_id": "CPTY-CORP-ALPHA",
            "facility_id": "FAC-ALPHA-01",
            "counterparty_exposure_record": {
                "counterparty_id": "CPTY-CORP-ALPHA",
                "total_facility_limit": 10000000.0,
                "current_drawn_exposure": 9500000.0,
                "currency": "USD",
                "is_breached": False,
                "is_authoritative": True,
            },
            "credit_facility_agreement": {
                "facility_id": "FAC-ALPHA-01",
                "borrower_entity": "CPTY-CORP-ALPHA",
            },
            "enterprise_risk_rating": {
                "counterparty_id": "CPTY-CORP-ALPHA",
                "rating": "AA",
            },
        },
    )
    out = harness.process_input(inp)
    assert out.stp_eligible is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.resolution_recommendation is not None
    assert "dossier_id" in out.resolution_recommendation
    assert out.resolution_recommendation.get("autonomous_stp_prohibited") is True

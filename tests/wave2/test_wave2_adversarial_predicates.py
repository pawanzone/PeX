"""Adversarial and 8-Predicate Conjunction Tests for Wave 2 Profiles.

Verifies the immutable 8-predicate formula:
STP_ELIGIBLE = E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre

Includes:
1. 12 PR-06 Adversarial Tests (Network timeouts masquerading as rejections, unmapped narrative, ambiguous hops, etc.)
2. 12 ST-02 Adversarial Tests (Replacement-account synthesis attempts, closed vs dormant, contradictory DDA, etc.)
3. 10 ST-03 Adversarial Tests (PNC vs PND, statutory sanctions blocks diverted, conflicting orders, etc.)
4. 8-Predicate Mutation Matrix across all 3 Wave 2 profiles (24 permutations).
"""
import pytest
from app.services.stp_engine import STPEngine
from app.schemas.policy_contract import STPEligibilityDecision
from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.policy_schemas import W2PolicyThresholds, BankPolicyEnvelope

WAVE2_PROFILES = [
    "PR-06",
    "ST-02",
    "ST-03"
]

PREDICATES = [
    "e_suff",
    "r_det",
    "r_uniq",
    "v_det",
    "v_auth",
    "p_bank",
    "c_comp",
    "x_pre"
]


class TestWave2EightPredicateMutationMatrix:
    """Rigorous mutation testing across all 8 predicates for all 3 Wave 2 profiles."""

    @pytest.mark.parametrize("profile", WAVE2_PROFILES)
    @pytest.mark.parametrize("failing_predicate", PREDICATES)
    def test_single_predicate_failure_forces_stp_ineligible(self, profile, failing_predicate):
        engine = STPEngine()
        kwargs = {p: True for p in PREDICATES}
        kwargs[failing_predicate] = False

        decision: STPEligibilityDecision = engine.evaluate_canonical_8_predicates(
            case_id=f"EX-ADV-W2-{profile}-{failing_predicate}",
            profile_id=profile,
            **kwargs,
            ai_confidence=0.99  # AI confidence must have 0% bypass authority
        )

        assert decision.stp_eligible is False, f"Formula breached: {profile} evaluated to STP_ELIGIBLE=True with {failing_predicate}=False"
        assert len(decision.policy_denial_reasons) >= 1
        assert any(failing_predicate.upper() in r.upper() for r in decision.policy_denial_reasons)

    @pytest.mark.parametrize("profile", WAVE2_PROFILES)
    def test_all_8_predicates_true_yields_stp_eligible(self, profile):
        engine = STPEngine()
        kwargs = {p: True for p in PREDICATES}

        decision: STPEligibilityDecision = engine.evaluate_canonical_8_predicates(
            case_id=f"EX-POS-W2-{profile}",
            profile_id=profile,
            **kwargs,
            ai_confidence=0.40
        )

        assert decision.stp_eligible is True
        assert len(decision.policy_denial_reasons) == 0


class TestWave2ProfileSpecificAdversarial:
    """34 Deep Profile-Specific Adversarial Scenarios (12 PR-06, 12 ST-02, 10 ST-03)."""

    @pytest.fixture
    def harness(self):
        return E2EExecutionHarness()

    # --------------------------------------------------------------------------
    # 1. PR-06 ADVERSARIAL TESTS (12 Scenarios)
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("scenario_id,adv_ctx", [
        ("ADV-PR06-01", {"is_telemetry_only": True}),
        ("ADV-PR06-02", {"socket_error": True}),
        ("ADV-PR06-03", {"unmapped_narrative": True}),
        ("ADV-PR06-04", {"compliance_hold_required": True}),
        ("ADV-PR06-05", {"multiple_competing_alternate_routes": True}),
        ("ADV-PR06-06", {"ambiguous_routing_paths": True}),
        ("ADV-PR06-07", {"simulate_authority_unavailable": True}),
        ("ADV-PR06-08", {"ofac_sanctions_hit": True}),
        ("ADV-PR06-09", {"rejection_advice": None}),
        ("ADV-PR06-10", {"duplicate_rejection_burst": True}),
        ("ADV-PR06-11", {"corridor_prohibited": True}),
        ("ADV-PR06-12", {"idempotency_locked": True}),
    ])
    def test_pr06_adversarial_scenarios(self, harness, scenario_id, adv_ctx):
        input_data = {
            "exception_id": f"EX-{scenario_id}",
            "profile_id": "PR-06",
            "payment_info": {
                "payment_id": f"PMT-{scenario_id}",
                "uetr": f"UETR-{scenario_id}-0001",
                "amount": 10000.0,
                "currency": "USD",
                "clearing_rail": "SWIFT_CBPR+",
                "debtor_agent_bic": "BNPAFRPPXXX",
                "creditor_agent_bic": "DEUTDEDDXXX"
            },
            "bank_supplied_evidence": {
                "inward_rejection_advice": {
                    "rejection_reference": f"REJ-{scenario_id}",
                    "original_uetr": f"UETR-{scenario_id}-0001",
                    "original_payment_id": f"PMT-{scenario_id}",
                    "rejecting_institution_bic": "BNPAFRPPXXX",
                    "rejection_code": "RC01",
                    "rejection_category": "ROUTING_UNREACHABLE",
                    "is_telemetry_only": False
                },
                "outbound_payment_record": {"status": "DISPATCHED"},
                "correspondent_ssi_directory": {"status": "ACTIVE"},
                "rail_cutoff_schedule": {"is_open": True},
                **adv_ctx
            }
        }
        res = harness.process_input(input_data)
        assert res.stp_eligible is False
        assert res.hitl_required is True
        assert res.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert res.execution_owner == "BANK"

    # --------------------------------------------------------------------------
    # 2. ST-02 ADVERSARIAL TESTS (12 Scenarios)
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("scenario_id,adv_ctx", [
        ("ADV-ST02-01", {"autonomous_replacement_attempt": True}),
        ("ADV-ST02-02", {"contradictory_account_status": True}),
        ("ADV-ST02-03", {"auxiliary_directory_active_conflict": True}),
        ("ADV-ST02-04", {"core_dda_status": "DORMANT"}), # Dormant != Closed
        ("ADV-ST02-05", {"core_dda_status": "ACTIVE"}),  # Active != Closed
        ("ADV-ST02-06", {"core_dda_status": "ADMINISTRATIVE_HOLD"}),
        ("ADV-ST02-07", {"rollover_mandate": {"dual_authorization_verified": False, "mandate_id": "M1", "closed_account_number": "99887700", "successor_account_number": "11112222", "authorized_signatory": "A", "signed_date": "2026-01-01"}}),
        ("ADV-ST02-08", {"simulate_authority_unavailable": True}),
        ("ADV-ST02-09", {"ofac_sanctions_hit": True}),
        ("ADV-ST02-10", {"account_status": None}),
        ("ADV-ST02-11", {"unauthorized_ai_account_substitution": True, "autonomous_replacement_attempt": True}),
        ("ADV-ST02-12", {"return_amount_exceeds_risk_policy": True}),
    ])
    def test_st02_adversarial_scenarios(self, harness, scenario_id, adv_ctx):
        input_data = {
            "exception_id": f"EX-{scenario_id}",
            "profile_id": "ST-02",
            "payment_info": {
                "payment_id": f"PMT-{scenario_id}",
                "uetr": f"UETR-{scenario_id}-0002",
                "amount": 250000.0 if "risk_policy" in scenario_id else 10000.0,
                "currency": "USD",
                "clearing_rail": "FEDWIRE",
                "creditor_account": "99887700"
            },
            "bank_supplied_evidence": {
                "core_dda_account_status": {"account_status": "CLOSED"},
                "inward_payment_record": {"amount": 10000.0},
                "clearing_return_schedule": {"status": "ACTIVE"},
                **adv_ctx
            }
        }
        res = harness.process_input(input_data)
        assert res.stp_eligible is False
        assert res.hitl_required is True
        assert res.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert res.execution_owner == "BANK"

    # --------------------------------------------------------------------------
    # 3. ST-03 ADVERSARIAL TESTS (10 Scenarios)
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("scenario_id,adv_ctx", [
        ("ADV-ST03-01", {"is_statutory_sanctions": True}), # Statutory Sanctions -> Divert to CO-01
        ("ADV-ST03-02", {"ofac_sdn_hit": True}),
        ("ADV-ST03-03", {"conflicting_legal_orders": True}),
        ("ADV-ST03-04", {"account_restriction_scope": {"restriction_type": "DEBIT_ONLY", "is_credit_prohibited": False, "restriction_reference_id": "R1", "issuing_authority": "COURT", "account_number": "33445566", "account_title": "TEST"}}),
        ("ADV-ST03-05", {"legal_freeze_dossier": None}),
        ("ADV-ST03-06", {"simulate_authority_unavailable": True}),
        ("ADV-ST03-07", {"autonomous_replacement_attempt": True}),
        ("ADV-ST03-08", {"statutory_asset_freeze_detected": True, "is_statutory_sanctions": True}),
        ("ADV-ST03-09", {"legal_freeze_dossier": {"dossier_id": "D-ERR", "account_number": "33445566", "case_caption": "C", "court_or_agency_name": "A", "docket_number": "DN", "freeze_type": "STATUTORY_ASSET_FREEZE", "is_conflicting_order": False, "permitted_disposition": "RETURN"}}),
        ("ADV-ST03-10", {"requested_disposition": "LEGAL_SUSPENSE_ESCROW", "policy_blocks_suspense": True}),
    ])
    def test_st03_adversarial_scenarios(self, harness, scenario_id, adv_ctx):
        input_data = {
            "exception_id": f"EX-{scenario_id}",
            "profile_id": "ST-03",
            "payment_info": {
                "payment_id": f"PMT-{scenario_id}",
                "uetr": f"UETR-{scenario_id}-0003",
                "amount": 25000.0,
                "currency": "USD",
                "clearing_rail": "FEDWIRE",
                "creditor_account": "33445566"
            },
            "bank_supplied_evidence": {
                "core_account_restriction_flag": {"restriction_type": "POST_NO_CREDITS", "is_credit_prohibited": True},
                "legal_freeze_dossier": {
                    "dossier_id": "DOS-2026-NY-9912",
                    "account_number": "33445566",
                    "case_caption": "Apex Creditors v. Metro Properties Holding LLC",
                    "court_or_agency_name": "New York State Supreme Court",
                    "docket_number": "Index No. 650123/2026",
                    "freeze_type": "COURT_INJUNCTION",
                    "permitted_disposition": "RETURN_TO_ORDERING_INSTITUTION"
                },
                "inward_payment_record": {"amount": 25000.0},
                "suspense_ledger_matrix": {"status": "CONFIGURED"},
                **adv_ctx
            }
        }
        res = harness.process_input(input_data)
        assert res.stp_eligible is False
        assert res.hitl_required is True
        assert res.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert res.execution_owner == "BANK"

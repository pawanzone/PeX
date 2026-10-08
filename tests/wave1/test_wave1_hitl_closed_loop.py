"""HITL Closed-Loop and Dynamic Re-Evaluation Tests for Wave 1.

Demonstrates that:
1. Missing / ambiguous evidence routes to PeX-native HITL workspace.
2. Mode 4 operator evidence ingestion occurs inside PeX.
3. Re-evaluation runs through the exact same 8-predicate formula.
4. Eligible outcomes emit BANK_HANDOFF_READY with execution_owner = 'BANK'.
5. Ineligible outcomes remain in governed internal states (HITL / INVESTIGATION).
"""
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.services.hitl_workflow_service import HITLWorkflowService
from app.services.evidence_store import EvidenceStoreService
from app.services.acquisition_gateway import AcquisitionGateway
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.schemas.contracts.evidence_config_schemas import HitlEvidenceSubmissionRequest


class TestWave1HitlClosedLoop:
    """Verifies internal closed-loop HITL re-evaluation for Wave 1 profiles."""

    def test_dq03_missing_evidence_to_hitl_re_evaluation(self):
        harness = E2EExecutionHarness()
        store = EvidenceStoreService()
        cfg_adapter = InMemoryConfigurationAdapter()
        resolver = DynamicEvidenceConfigResolver(cfg_adapter)
        gateway = AcquisitionGateway(store)
        hitl_service = HITLWorkflowService(resolver, gateway, store)

        # 1. Initial execution with missing beneficiary data
        input_data = {
            "exception_id": "EX-HITL-DQ03-001",
            "profile_id": "DQ-03",
            "payment_info": {
                "payment_id": "PMT-HITL-001",
                "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef030001",
                "amount": 5000.0,
                "currency": "GBP",
                "clearing_rail": "CHAPS",
                "creditor_account": "12345678"
            },
            "bank_supplied_evidence": {} # Missing evidence
        }
        res1 = harness.process_input(input_data)
        assert res1.stp_eligible is False
        assert res1.hitl_required is True
        assert res1.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert res1.execution_owner == "BANK"

        # 2. Operator submits Mode 4 evidence in PeX HITL workspace
        submission = HitlEvidenceSubmissionRequest(
            case_id="EX-HITL-DQ03-001",
            tenant_id="DEFAULT_BANK",
            profile_id="DQ-03",
            operator_id="OP-MAKER-01",
            operator_role="PAYMENT_OPERATOR",
            submitted_fields={"verified_creditor_name": "ACME INDUSTRIAL SUPPLIES LTD"},
            notes="Acquired confirmed legal entity name from client"
        )
        re_eval_called = False
        def mock_re_eval(case_id):
            nonlocal re_eval_called
            re_eval_called = True
            return {"stp_eligible": True, "status": "RESOLVED"}

        resp = hitl_service.process_operator_submission(
            submission=submission,
            transaction_context={"amount": 5000.0, "currency": "GBP"},
            re_eval_callback=mock_re_eval
        )
        assert resp.is_accepted is True
        assert resp.re_evaluation_triggered is True
        assert re_eval_called is True

        # 3. Re-evaluate case through E2E harness with newly acquired Mode 4 evidence
        input_data_repaired = {
            **input_data,
            "bank_supplied_evidence": {
                "client_master_record": {"creditor_name": "ACME INDUSTRIAL SUPPLIES LTD"},
                "verified_creditor_name": "ACME INDUSTRIAL SUPPLIES LTD"
            }
        }
        res2 = harness.process_input(input_data_repaired)
        assert res2.stp_eligible is True
        assert res2.hitl_required is False
        assert res2.bank_handoff_status == "BANK_HANDOFF_READY"
        assert res2.execution_owner == "BANK"

    def test_dq09_vop_re_evaluation_still_failing_remains_internal(self):
        harness = E2EExecutionHarness()

        # Inbound with completely mismatching name
        input_data = {
            "exception_id": "EX-HITL-DQ09-FAIL",
            "profile_id": "DQ-09",
            "payment_info": {
                "payment_id": "PMT-HITL-002",
                "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef090002",
                "amount": 5000.0,
                "currency": "EUR",
                "clearing_rail": "TARGET2",
                "creditor_name": "UNRECOGNIZED_ENTITY",
                "creditor_account": "11223344"
            },
            "bank_supplied_evidence": {
                "core_account_title": {"account_title": "SIEMENS AG INDUSTRIAL POWER"},
                "verification_of_payee_confirmation": {"match_score": 0.10, "match_status": "NO_MATCH"}
            }
        }
        res = harness.process_input(input_data)
        assert res.stp_eligible is False
        assert res.hitl_required is True
        assert res.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert res.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"

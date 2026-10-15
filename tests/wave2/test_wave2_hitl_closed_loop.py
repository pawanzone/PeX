"""HITL Closed-Loop and Dynamic Re-Evaluation Tests for Wave 2.

Demonstrates:
1. Missing/ambiguous evidence routes to PeX-native HITL workspace.
2. Mode 4 operator evidence ingestion occurs strictly inside PeX.
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


class TestWave2HitlClosedLoop:
    """Verifies internal closed-loop HITL re-evaluation for Wave 2 profiles."""

    def test_pr06_missing_alternate_hop_to_hitl_re_evaluation(self):
        harness = E2EExecutionHarness()
        store = EvidenceStoreService()
        cfg_adapter = InMemoryConfigurationAdapter()
        resolver = DynamicEvidenceConfigResolver(cfg_adapter)
        gateway = AcquisitionGateway(store)
        hitl_service = HITLWorkflowService(resolver, gateway, store)

        # 1. Initial execution with missing alternate correspondent BIC
        input_data = {
            "exception_id": "EX-HITL-PR06-001",
            "profile_id": "PR-06",
            "payment_info": {
                "payment_id": "PMT-HITL-PR06-001",
                "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef060001",
                "amount": 15000.0,
                "currency": "USD",
                "clearing_rail": "SWIFT_CBPR+",
                "debtor_agent_bic": "BNPAFRPPXXX",
                "creditor_agent_bic": "DEUTDEDDXXX"
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
            case_id="EX-HITL-PR06-001",
            tenant_id="DEFAULT_BANK",
            profile_id="PR-06",
            operator_id="OP-CLEARING-01",
            operator_role="CLEARING_OPERATIONS_ANALYST",
            submitted_fields={"verified_alternate_intermediary_bic": "CHASUS33XXX"},
            notes="Acquired verified secondary Nostro correspondent BIC from SWIFT directory"
        )
        resp = hitl_service.process_operator_submission(
            submission=submission,
            transaction_context={"amount": 15000.0, "currency": "USD"},
            re_eval_callback=lambda cid: {"stp_eligible": True, "status": "RESOLVED"}
        )
        assert resp.is_accepted is True
        assert resp.re_evaluation_triggered is True

        # 3. Re-evaluate case through E2E harness with newly acquired Mode 4 evidence
        input_data_repaired = {
            **input_data,
            "bank_supplied_evidence": {
                "inward_rejection_advice": {
                    "rejection_reference": "REJ-2026-PR06-001",
                    "original_uetr": "9f1e2d3c-4b5a-6789-0123-abcdef060001",
                    "original_payment_id": "PMT-HITL-PR06-001",
                    "rejecting_institution_bic": "BNPAFRPPXXX",
                    "rejection_code": "RC01",
                    "rejection_category": "ROUTING_UNREACHABLE",
                    "is_telemetry_only": False
                },
                "outbound_payment_record": {"status": "DISPATCHED"},
                "correspondent_ssi_directory": {"status": "ACTIVE"},
                "rail_cutoff_schedule": {"is_open": True},
                "verified_alternate_intermediary_bic": "CHASUS33XXX"
            }
        }
        res2 = harness.process_input(input_data_repaired)
        assert res2.stp_eligible is True
        assert res2.hitl_required is False
        assert res2.bank_handoff_status == "BANK_HANDOFF_READY"
        assert res2.execution_owner == "BANK"

    def test_st02_missing_status_to_hitl_re_evaluation(self):
        harness = E2EExecutionHarness()

        input_data_missing = {
            "exception_id": "EX-HITL-ST02-001",
            "profile_id": "ST-02",
            "payment_info": {
                "payment_id": "PMT-HITL-ST02-001",
                "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef020001",
                "amount": 10000.0,
                "currency": "USD",
                "clearing_rail": "FEDWIRE",
                "creditor_account": "99887700"
            },
            "bank_supplied_evidence": {} # Missing Core DDA status
        }
        res1 = harness.process_input(input_data_missing)
        assert res1.stp_eligible is False
        assert res1.hitl_required is True

        input_data_repaired = {
            **input_data_missing,
            "bank_supplied_evidence": {
                "core_dda_account_status": {"account_status": "CLOSED"},
                "inward_payment_record": {"amount": 10000.0},
                "clearing_return_schedule": {"status": "ACTIVE"}
            }
        }
        res2 = harness.process_input(input_data_repaired)
        assert res2.stp_eligible is True
        assert res2.bank_handoff_status == "BANK_HANDOFF_READY"
        assert res2.execution_owner == "BANK"

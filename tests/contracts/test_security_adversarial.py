"""Security and Adversarial Contract Tests for Wave 0A.

Tests:
1. Idempotency race condition and replay prevention
2. Cryptographic audit chain tamper detection
3. Maker == Checker Segregation of Duties violation rejection
4. Secret Token Vault PII isolation and unauthorized detokenization rejection
5. Zero PII leakage before AI context boundary
"""
import pytest

from app.adapters.reference.reference_idempotency_adapter import InMemoryIdempotencyAdapter
from app.adapters.reference.reference_token_vault_adapter import InMemorySecretTokenizationVaultAdapter
from app.adapters.reference.reference_audit_adapter import InMemoryAuditLedgerAdapter
from app.adapters.reference.reference_bank_handoff_adapter import InMemoryBankHandoffAdapter
from app.schemas.contracts.token_vault_schemas import DetokenizationRequest
from app.schemas.contracts.audit_schemas import AuditBlockPayload
from app.schemas.contracts.bank_handoff_schemas import (
    ApprovalSignature,
    DispatchIntent,
    ExecutionOwner,
    HandoffStatus,
)


class TestSecurityAdversarial:
    """Adversarial and security boundary test suite."""

    def test_idempotency_double_acquire_lock_contention(self):
        adapter = InMemoryIdempotencyAdapter()
        res1 = adapter.acquire_lock("KEY-001", "PROCESSOR-A", lease_duration_ms=10000)
        assert res1.status.value == "ACQUIRED"
        assert res1.fencing_token == 1

        # Concurrent processor tries to acquire same key
        res2 = adapter.acquire_lock("KEY-001", "PROCESSOR-B", lease_duration_ms=10000)
        assert res2.status.value == "LOCKED_BY_OTHER"
        assert res2.holder_id == "PROCESSOR-A"

    def test_idempotency_replay_after_execution_records_state(self):
        adapter = InMemoryIdempotencyAdapter()
        adapter.acquire_lock("KEY-002", "PROCESSOR-A")
        adapter.record_execution("KEY-002", {"status": "SETTLED", "tx_id": "TX-99"})

        # Subsequent re-transmission attempt
        res_replay = adapter.acquire_lock("KEY-002", "PROCESSOR-A")
        assert res_replay.status.value == "ALREADY_EXECUTED"
        assert res_replay.existing_execution_result["tx_id"] == "TX-99"

    def test_audit_hash_chain_tamper_detection(self):
        ledger = InMemoryAuditLedgerAdapter()
        
        # Append 3 blocks
        for i in range(1, 4):
            p = AuditBlockPayload(
                event_id=f"EVT-{i}",
                case_id="PEX-SEC-01",
                correlation_id="UETR-SEC-01",
                stage_name=f"STAGE_{i}",
                actor_id="USER-A",
                actor_role="MAKER",
                action_name="ACTION",
                details=f"Block {i} commit"
            )
            ledger.append_event(p)

        assert ledger.verify_integrity() is True

        # Adversarial tampering: modify payload in block 2
        ledger._chain[1].payload.details = "TAMPERED DETAILS BY ADVERSARY"
        assert ledger.verify_integrity() is False

    def test_maker_checker_same_identity_rejection(self):
        adapter = InMemoryBankHandoffAdapter()
        intent = DispatchIntent(
            intent_id="INT-001",
            action_type="REPAIR_AND_RELEASE",
            target_clearing_rail="FEDWIRE"
        )
        
        # Adversarial attempt: Maker approves as Checker
        signatures = [
            ApprovalSignature(
                approval_id="SIG-1",
                approver_id="USER-JOHN-DOE",
                approver_name="John Doe",
                approver_role="OPERATIONS_MAKER",
                action="APPROVE"
            ),
            ApprovalSignature(
                approval_id="SIG-2",
                approver_id="USER-JOHN-DOE", # SAME IDENTIFIER
                approver_name="John Doe",
                approver_role="OPERATIONS_CHECKER",
                action="DUAL_AUTHORIZE"
            )
        ]

        envelope = adapter.create_handoff_envelope(
            case_id="PEX-MC-01",
            payment_id="PMT-01",
            uetr="UETR-01",
            dispatch_intent=intent,
            stp_eligible=False,
            stp_formula_evaluation={},
            signatures=signatures,
            audit_block_hash="HASH-01"
        )

        # Validation must reject Maker == Checker
        is_valid = adapter.validate_handoff_envelope(envelope)
        assert is_valid is False

    def test_unauthorized_detokenization_caller_rejection(self):
        vault = InMemorySecretTokenizationVaultAdapter()
        tok = vault.tokenize_value("GB82WEST12345698765432", "IBAN")
        
        # Unauthorized caller attempt
        req = DetokenizationRequest(
            token=tok.token,
            caller_role="UNAUTHORIZED_EXTERNAL_USER"
        )
        with pytest.raises(PermissionError):
            vault.detokenize_value(req)

        # Authorized caller succeeds
        req_auth = DetokenizationRequest(
            token=tok.token,
            caller_role="BANK_GATEWAY_OUTBOUND"
        )
        assert vault.detokenize_value(req_auth) == "GB82WEST12345698765432"

    def test_zero_pii_token_format_is_safe_for_ai(self):
        vault = InMemorySecretTokenizationVaultAdapter()
        tok = vault.tokenize_value("40051512345678", "ACCOUNT")
        assert "40051512345678" not in tok.token
        assert tok.token.startswith("TOK-ACC-")
        assert tok.is_safe_for_ai_context is True

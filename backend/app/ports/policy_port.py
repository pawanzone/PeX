"""Bank Policy Envelope Port (SPI).

Defines the abstract interface for retrieving active bank policy envelopes and evaluating
transaction actions against risk ceilings, compliance rules, and Maker-Checker policies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.policy_schemas import (
    BankPolicyEnvelope,
    PolicyEvaluationResult,
)


class BankPolicyEnvelopePort(ABC):
    """Abstract port for bank risk and operational policy evaluation."""

    @abstractmethod
    def get_active_policy(self, bank_id: Optional[str] = None) -> Optional[BankPolicyEnvelope]:
        """Retrieves the active bank policy envelope. Returns None if missing (fail closed)."""
        pass

    @abstractmethod
    def evaluate_transaction(
        self,
        policy: BankPolicyEnvelope,
        profile_id: str,
        amount: float,
        currency: str,
        action_type: str,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> PolicyEvaluationResult:
        """Evaluates whether the action is permitted under bank policy (P_bank predicate)."""
        pass

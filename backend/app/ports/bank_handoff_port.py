"""Bank Handoff Envelope Port (SPI).

Defines the abstract interface for assembling, cryptographically sealing, and delivering
the terminal resolution package to the bank's execution gateway.
Universal Postcondition: BANK_HANDOFF_READY with execution_owner = "BANK".
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.bank_handoff_schemas import (
    BankHandoffEnvelope,
    ApprovalSignature,
    DispatchIntent,
)


class BankHandoffEnvelopePort(ABC):
    """Abstract port for sealing and delivering terminal handoff packages."""

    @abstractmethod
    def create_handoff_envelope(
        self,
        case_id: str,
        payment_id: str,
        uetr: str,
        dispatch_intent: DispatchIntent,
        stp_eligible: bool,
        stp_formula_evaluation: Dict[str, Any],
        signatures: List[ApprovalSignature],
        audit_block_hash: str,
        is_autonomous_zero_touch: bool = False
    ) -> BankHandoffEnvelope:
        """Assembles and seals a BankHandoffEnvelope."""
        pass

    @abstractmethod
    def validate_handoff_envelope(
        self,
        envelope: BankHandoffEnvelope
    ) -> bool:
        """Validates that execution_owner is BANK, signatures match Segregation of Duties, and envelope is sealed."""
        pass

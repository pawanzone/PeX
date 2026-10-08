"""Account Master & Verification of Payee Port (SPI).

Defines abstract SPI for querying authoritative client master data, account ownership,
and Verification of Payee (VoP / Confirmation of Payee) matching.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    AccountMasterRecord,
    BeneficiaryProfileRecord,
    PayeeVerificationResult,
)


class AccountMasterPort(ABC):
    """Abstract port for Account Master & Confirmation of Payee lookups."""

    @abstractmethod
    def get_account_master(self, account_number: str) -> Optional[AccountMasterRecord]:
        """Retrieves authoritative account master record from Core DDA / Account Directory."""
        pass

    @abstractmethod
    def verify_payee(
        self,
        account_number: str,
        payee_name: str,
        account_type: Optional[str] = None
    ) -> PayeeVerificationResult:
        """Executes Verification of Payee (VoP) scoring against authoritative account title."""
        pass

    @abstractmethod
    def lookup_beneficiary_profile(
        self,
        debtor_id: str,
        creditor_hint: str
    ) -> Optional[BeneficiaryProfileRecord]:
        """Looks up standing client master directory record for a recurring beneficiary."""
        pass

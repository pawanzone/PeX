"""Nostro Position & Liquidity Port (SPI).

Defines abstract SPI for querying correspondent Nostro balances, tracking incoming
settlement credits, and packaging rebalancing candidates for TR-03 (Nostro Shortfall).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    NostroPositionRecord,
    PendingCorrespondentCreditRecord,
    NostroRebalancingCandidate,
)


class NostroPositionPort(ABC):
    """Abstract port for Nostro Position and Rebalancing operations."""

    @abstractmethod
    def get_nostro_position(
        self, nostro_bic: str, currency: str
    ) -> Optional[NostroPositionRecord]:
        """Retrieves authoritative Nostro account position from Treasury Management."""
        pass

    @abstractmethod
    def get_pending_correspondent_credits(
        self, nostro_bic: str, currency: str
    ) -> List[PendingCorrespondentCreditRecord]:
        """Retrieves expected pending clearing credits for a Nostro account."""
        pass

    @abstractmethod
    def generate_rebalancing_candidate(
        self, target_nostro_bic: str, required_amount: float, currency: str
    ) -> Optional[NostroRebalancingCandidate]:
        """Packages an interbank Nostro liquidity sweep or rebalancing candidate."""
        pass

"""In-Memory Reference Nostro Position & Rebalancing Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements NostroPositionPort (SPI-NOSTRO-POSITION).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.nostro_position_port import NostroPositionPort
from app.schemas.contracts.wave3_schemas import (
    NostroPositionRecord,
    PendingCorrespondentCreditRecord,
    NostroRebalancingCandidate,
)


class InMemoryNostroPositionAdapter(NostroPositionPort):
    """Hermetic reference implementation of NostroPositionPort."""

    def __init__(
        self,
        positions: Optional[Dict[str, NostroPositionRecord]] = None,
        pending_credits: Optional[Dict[str, List[PendingCorrespondentCreditRecord]]] = None,
    ):
        self._positions: Dict[str, NostroPositionRecord] = positions or {
            "BNPAFRPPXXX:EUR": NostroPositionRecord(
                nostro_bic="BNPAFRPPXXX",
                currency="EUR",
                available_balance=50000.0,
                ledger_balance=100000.0,
                minimum_operating_target=200000.0,
                is_authoritative=True,
                authority_source="TREASURY_MANAGEMENT_SYSTEM",
            ),
            "CHASUS33XXX:USD": NostroPositionRecord(
                nostro_bic="CHASUS33XXX",
                currency="USD",
                available_balance=15000000.0,
                ledger_balance=15000000.0,
                minimum_operating_target=5000000.0,
                is_authoritative=True,
                authority_source="TREASURY_MANAGEMENT_SYSTEM",
            ),
            "DEUTDEDDXXX:EUR": NostroPositionRecord(
                nostro_bic="DEUTDEDDXXX",
                currency="EUR",
                available_balance=5000000.0,
                ledger_balance=5000000.0,
                minimum_operating_target=1000000.0,
                is_authoritative=True,
                authority_source="TREASURY_MANAGEMENT_SYSTEM",
            ),
        }
        self._pending_credits: Dict[str, List[PendingCorrespondentCreditRecord]] = pending_credits or {
            "BNPAFRPPXXX:EUR": [
                PendingCorrespondentCreditRecord(
                    credit_reference="CR-2026-EUR-001",
                    target_nostro_bic="BNPAFRPPXXX",
                    currency="EUR",
                    expected_amount=300000.0,
                    clearing_rail="TARGET2",
                    confidence_score=1.0,
                )
            ]
        }

    def get_nostro_position(
        self, nostro_bic: str, currency: str
    ) -> Optional[NostroPositionRecord]:
        key = f"{nostro_bic.strip()}:{currency.strip().upper()}"
        return self._positions.get(key)

    def register_nostro_position(self, position: NostroPositionRecord) -> None:
        key = f"{position.nostro_bic}:{position.currency}"
        self._positions[key] = position

    def get_pending_credits(self, nostro_bic: str, currency: str) -> List[PendingCorrespondentCreditRecord]:
        key = f"{nostro_bic.strip()}:{currency.strip().upper()}"
        return self._pending_credits.get(key, [])

    def get_pending_correspondent_credits(
        self, nostro_bic: str, currency: str
    ) -> List[PendingCorrespondentCreditRecord]:
        return self.get_pending_credits(nostro_bic, currency)

    def generate_rebalancing_candidate(
        self, target_nostro_bic: str, required_amount: float, currency: str
    ) -> Optional[NostroRebalancingCandidate]:
        pos = self.get_nostro_position(target_nostro_bic, currency)
        deficit = required_amount - (pos.available_balance if pos else 0.0)
        if deficit <= 0:
            return None

        # Determine funding source from pools with excess headroom
        funding_acct = "NOSTRO-MASTER-EUR" if currency.upper() == "EUR" else "NOSTRO-CENTRAL-USD"
        return NostroRebalancingCandidate(
            candidate_id=f"REBAL-{uuid.uuid4().hex[:8].upper()}",
            target_nostro_bic=target_nostro_bic,
            funding_nostro_account=funding_acct,
            rebalancing_amount=deficit + 50000.0,  # Include buffer
            currency=currency.upper(),
            recommended_pacing_seconds=120.0,
            execution_owner="BANK",
            rationale=f"Automated Nostro sweep from {funding_acct} to cover settlement deficit of {deficit} {currency}",
        )

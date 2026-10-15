"""In-Memory Reference Settlement Return Adapter.

TEST / REFERENCE ONLY.
Implements SettlementReturnPort (SPI-SETTLEMENT-RETURN-PORT).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.settlement_return_port import SettlementReturnPort
from app.schemas.contracts.wave2_schemas import SettlementReturnPackage


class InMemorySettlementReturnAdapter(SettlementReturnPort):
    """Hermetic reference implementation of SettlementReturnPort."""

    def __init__(self):
        self._packages: Dict[str, SettlementReturnPackage] = {}

    def generate_return_package(
        self,
        uetr: str,
        original_payment_id: str,
        amount: float,
        currency: str,
        return_reason_code: str,
        clearing_rail: str,
        narrative: Optional[str] = None,
        debtor_account: Optional[str] = None
    ) -> SettlementReturnPackage:
        return_id = f"RET-{clearing_rail}-{uuid.uuid4().hex[:8].upper()}"
        default_narratives = {
            "AC04": "Account closed / terminated in Core DDA.",
            "PNC": "Account subject to Post No Credits restriction.",
            "FR01": "Account frozen by judicial order / court restraint.",
            "RC01": "Intermediary bank rejection - no viable alternate routing path.",
            "MD07": "End customer deceased or legal entity dissolved.",
        }
        narr = narrative or default_narratives.get(return_reason_code, f"Return generated under reason {return_reason_code}")

        pkg = SettlementReturnPackage(
            return_id=return_id,
            original_uetr=uetr,
            original_payment_id=original_payment_id,
            return_amount=amount,
            currency=currency,
            return_reason_code=return_reason_code,
            return_reason_narrative=narr,
            debtor_recredit_account=debtor_account or "GL-1090-RETURN-SETTLEMENT",
            creditor_nostro_account="GL-1010-FEDWIRE-NOSTRO",
            target_clearing_rail=clearing_rail,
            return_mechanism="pacs.004_or_rail_return",
            is_fully_balanced=True,
            generated_at=datetime.now(timezone.utc)
        )
        self._packages[return_id] = pkg
        return pkg

    def validate_return_schema(self, return_package: SettlementReturnPackage) -> bool:
        if not return_package.return_id or not return_package.original_uetr:
            return False
        if return_package.return_amount <= 0.0:
            return False
        if not return_package.return_reason_code:
            return False
        return return_package.is_fully_balanced

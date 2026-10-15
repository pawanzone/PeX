"""In-Memory Reference Correspondent Gateway Adapter.

TEST / REFERENCE ONLY.
Implements CorrespondentGatewayPort (SPI-CORRESPONDENT-GATEWAY).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.correspondent_gateway_port import CorrespondentGatewayPort
from app.schemas.contracts.wave2_schemas import (
    IntermediaryRejectionAdvice,
    IntermediaryRejectionReasonCode,
    DeterministicCorrelationMatch,
)


class InMemoryCorrespondentGatewayAdapter(CorrespondentGatewayPort):
    """Hermetic reference implementation of CorrespondentGatewayPort."""

    def __init__(self, rejection_advices: Optional[Dict[str, IntermediaryRejectionAdvice]] = None):
        self._advices: Dict[str, IntermediaryRejectionAdvice] = rejection_advices or {
            "REJ-2026-PR06-001": IntermediaryRejectionAdvice(
                rejection_reference="REJ-2026-PR06-001",
                original_uetr="9f1e2d3c-4b5a-6789-0123-abcdef060001",
                original_payment_id="PMT-2026-PR06-001",
                rejecting_institution_bic="BNPAFRPPXXX",
                intermediary_role="INTERMEDIARY_AGENT",
                rejection_code="RC01",
                rejection_category=IntermediaryRejectionReasonCode.ROUTING_UNREACHABLE,
                narrative_text="Intermediary routing channel temporarily suspended; please reroute via secondary clearing member.",
                is_telemetry_only=False,
                rejection_timestamp=datetime.now(timezone.utc)
            ),
            "REJ-2026-PR06-TEL": IntermediaryRejectionAdvice(
                rejection_reference="REJ-2026-PR06-TEL",
                original_uetr="9f1e2d3c-4b5a-6789-0123-abcdef060002",
                original_payment_id="PMT-2026-PR06-002",
                rejecting_institution_bic="CHASUS33XXX",
                intermediary_role="INTERMEDIARY_AGENT",
                rejection_code="SOCKET_RST",
                rejection_category=IntermediaryRejectionReasonCode.SOCKET_ERROR_TELEMETRY,
                narrative_text="TCP Connection reset by peer at gateway layer.",
                is_telemetry_only=True,
                rejection_timestamp=datetime.now(timezone.utc)
            )
        }

    def get_rejection_advice(self, rejection_reference_or_uetr: str) -> Optional[IntermediaryRejectionAdvice]:
        ref = rejection_reference_or_uetr.strip()
        if ref in self._advices:
            return self._advices[ref]
        for adv in self._advices.values():
            if adv.original_uetr == ref or adv.original_payment_id == ref:
                return adv
        return None

    def register_rejection_advice(self, advice: IntermediaryRejectionAdvice) -> None:
        self._advices[advice.rejection_reference] = advice

    def correlate_rejection(
        self,
        rejection_advice: IntermediaryRejectionAdvice,
        payment_context: Dict[str, Any]
    ) -> DeterministicCorrelationMatch:
        uetr = payment_context.get("uetr") or rejection_advice.original_uetr
        amt = float(payment_context.get("amount", 0.0))
        ccy = payment_context.get("currency", "USD")
        debtor_bic = payment_context.get("debtor_agent_bic", "CHASUS33XXX")
        creditor_bic = payment_context.get("creditor_agent_bic", "DEUTDEDDXXX")

        return DeterministicCorrelationMatch(
            original_uetr=uetr,
            original_payment_id=payment_context.get("payment_id", rejection_advice.original_payment_id),
            settlement_amount=amt,
            currency=ccy,
            debtor_agent_bic=debtor_bic,
            creditor_agent_bic=creditor_bic,
            correlation_confidence=1.0,
            is_unambiguous_match=True,
            match_keys_used=["uetr", "amount", "currency", "creditor_bic"]
        )

    def verify_rejection_authority(self, rejection_advice: IntermediaryRejectionAdvice) -> bool:
        # If marked as telemetry only, it is NOT sovereign rejection authority
        if rejection_advice.is_telemetry_only or rejection_advice.rejection_category == IntermediaryRejectionReasonCode.SOCKET_ERROR_TELEMETRY:
            return False
        return True

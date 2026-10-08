"""In-Memory Reference Gateway Socket Probe & Retry Adapter.

TEST / REFERENCE ONLY.
Implements GatewaySocketProbePort with deterministic connection probe, transmission check, and retry budgeting.
Zero vendor SDK dependencies.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.ports.gateway_socket_probe_port import GatewaySocketProbePort
from app.schemas.contracts.wave1_schemas import (
    GatewayProbeResult,
    TransmissionStateResult,
    RetryBudgetResult,
)


class InMemoryGatewaySocketAdapter(GatewaySocketProbePort):
    """Hermetic reference implementation of GatewaySocketProbePort."""

    def __init__(
        self,
        gateways: Optional[Dict[str, GatewayProbeResult]] = None,
        transmissions: Optional[Dict[str, TransmissionStateResult]] = None,
        budgets: Optional[Dict[str, RetryBudgetResult]] = None
    ):
        self._gateways: Dict[str, GatewayProbeResult] = gateways or {
            "GW-FEDWIRE-01": GatewayProbeResult(gateway_id="GW-FEDWIRE-01", rail_code="FEDWIRE", socket_status="HEALTHY", is_socket_connected=True, latency_ms=1.2),
            "GW-CHAPS-01": GatewayProbeResult(gateway_id="GW-CHAPS-01", rail_code="CHAPS", socket_status="HEALTHY", is_socket_connected=True, latency_ms=2.4),
            "GW-TARGET2-01": GatewayProbeResult(gateway_id="GW-TARGET2-01", rail_code="TARGET2", socket_status="HEALTHY", is_socket_connected=True, latency_ms=1.8),
            "GW-SWIFT-01": GatewayProbeResult(gateway_id="GW-SWIFT-01", rail_code="SWIFT_CBPR+", socket_status="HEALTHY", is_socket_connected=True, latency_ms=3.1),
        }

        self._transmissions: Dict[str, TransmissionStateResult] = transmissions or {
            "9f1e2d3c-4b5a-6789-0123-abcdef070001": TransmissionStateResult(
                payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef070001",
                transmission_status="TIMED_OUT",
                is_execution_settled=False,
                can_safely_retry=True,
                gateway_reference_id="GW-REF-2026-TIMEOUT"
            ),
            "9f1e2d3c-4b5a-6789-0123-abcdef070002": TransmissionStateResult(
                payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef070002",
                transmission_status="SETTLED",
                is_execution_settled=True,
                can_safely_retry=False,
                gateway_reference_id="GW-REF-2026-SETTLED"
            )
        }

        self._budgets: Dict[str, RetryBudgetResult] = budgets or {
            "PMT-PR07-001": RetryBudgetResult(payment_id="PMT-PR07-001", max_retries=3, retries_exhausted=0, can_retry=True),
            "PMT-PR07-EXHAUSTED": RetryBudgetResult(payment_id="PMT-PR07-EXHAUSTED", max_retries=3, retries_exhausted=3, can_retry=False)
        }

    def probe_gateway_socket(
        self,
        gateway_id: str,
        rail_code: str
    ) -> GatewayProbeResult:
        if gateway_id in self._gateways:
            return self._gateways[gateway_id]
        return GatewayProbeResult(
            gateway_id=gateway_id,
            rail_code=rail_code,
            socket_status="HEALTHY",
            is_socket_connected=True,
            latency_ms=1.5
        )

    def check_transmission_state(
        self,
        payment_uetr: str
    ) -> TransmissionStateResult:
        if payment_uetr in self._transmissions:
            return self._transmissions[payment_uetr]
        # Default: safe to retry if not confirmed settled
        return TransmissionStateResult(
            payment_uetr=payment_uetr,
            transmission_status="TIMED_OUT",
            is_execution_settled=False,
            can_safely_retry=True
        )

    def get_retry_budget(
        self,
        payment_id: str
    ) -> RetryBudgetResult:
        if payment_id in self._budgets:
            return self._budgets[payment_id]
        return RetryBudgetResult(payment_id=payment_id, max_retries=3, retries_exhausted=0, can_retry=True)

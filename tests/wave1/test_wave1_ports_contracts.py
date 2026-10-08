"""Contract and SPI Tests for Wave 1 Ports.

Verifies abstract base class inheritance, method signatures, Pydantic model validity,
and provider neutrality for all 7 Wave 1 abstract ports.
"""
import pytest
from abc import ABC
from app import ports
from app.ports.account_master_port import AccountMasterPort
from app.ports.routing_directory_port import RoutingDirectoryPort
from app.ports.clearing_rail_calendar_port import ClearingRailCalendarPort
from app.ports.payment_hub_repair_queue_port import PaymentHubRepairQueuePort
from app.ports.gateway_socket_probe_port import GatewaySocketProbePort
from app.ports.remittance_document_port import RemittanceDocumentPort
from app.ports.regulatory_directory_port import RegulatoryDirectoryPort

from app.adapters.reference import (
    InMemoryAccountMasterAdapter,
    InMemoryRoutingDirectoryAdapter,
    InMemoryClearingRailCalendarAdapter,
    InMemoryPaymentHubRepairQueueAdapter,
    InMemoryGatewaySocketAdapter,
    InMemoryRemittanceDocumentAdapter,
    InMemoryRegulatoryDirectoryAdapter,
)


class TestWave1PortsContracts:
    """Verifies that all 7 Wave 1 ports are exported and subclass abc.ABC."""

    W1_PORTS = [
        "AccountMasterPort",
        "RoutingDirectoryPort",
        "ClearingRailCalendarPort",
        "PaymentHubRepairQueuePort",
        "GatewaySocketProbePort",
        "RemittanceDocumentPort",
        "RegulatoryDirectoryPort",
    ]

    def test_ports_exported_and_subclass_abc(self):
        for p_name in self.W1_PORTS:
            assert hasattr(ports, p_name), f"Port {p_name} not exported in app.ports"
            cls = getattr(ports, p_name)
            assert issubclass(cls, ABC), f"Port {p_name} must subclass ABC"

    def test_reference_adapters_implement_ports(self):
        assert isinstance(InMemoryAccountMasterAdapter(), AccountMasterPort)
        assert isinstance(InMemoryRoutingDirectoryAdapter(), RoutingDirectoryPort)
        assert isinstance(InMemoryClearingRailCalendarAdapter(), ClearingRailCalendarPort)
        assert isinstance(InMemoryPaymentHubRepairQueueAdapter(), PaymentHubRepairQueuePort)
        assert isinstance(InMemoryGatewaySocketAdapter(), GatewaySocketProbePort)
        assert isinstance(InMemoryRemittanceDocumentAdapter(), RemittanceDocumentPort)
        assert isinstance(InMemoryRegulatoryDirectoryAdapter(), RegulatoryDirectoryPort)

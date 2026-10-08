"""Provider Neutrality Tests for Wave 0A Platform Ports.

Verifies that all files under backend/app/ports/ have zero imports of third-party
cloud SDKs (boto3, azure, google, redis, kafka, etc.) and adhere strictly to abstract SPI standards.
"""
import ast
from pathlib import Path
import pytest


class TestProviderNeutrality:
    """Verifies that ports are 100% cloud and vendor neutral."""

    FORBIDDEN_SDK_MODULES = [
        "boto3", "botocore", "azure", "google.cloud", "redis", "kafka",
        "pika", "pymongo", "psycopg2", "cx_Oracle", "ibm_db", "openai", "anthropic"
    ]

    def test_ports_have_zero_vendor_sdk_dependencies(self):
        ports_dir = Path("backend/app/ports")
        assert ports_dir.exists(), "backend/app/ports directory must exist"

        port_files = list(ports_dir.glob("*.py"))
        assert len(port_files) >= 13, f"Expected at least 13 port files, found {len(port_files)}"

        for p_file in port_files:
            tree = ast.parse(p_file.read_text(encoding="utf-8"), filename=str(p_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in self.FORBIDDEN_SDK_MODULES:
                            assert not alias.name.startswith(forbidden), f"Forbidden vendor SDK '{alias.name}' imported in {p_file.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in self.FORBIDDEN_SDK_MODULES:
                            assert not node.module.startswith(forbidden), f"Forbidden vendor SDK '{node.module}' imported in {p_file.name}"

    def test_all_13_ports_are_abstract_base_classes(self):
        from app import ports
        from abc import ABC

        expected_ports = [
            "EvidencePackagePort",
            "ContextualAuthorityPort",
            "BankPolicyEnvelopePort",
            "DistributedIdempotencyPort",
            "StreamingMessageBrokerPort",
            "CoreBankingDDAPort",
            "RegulatoryScreeningPort",
            "SecretTokenizationVaultPort",
            "AuditLedgerPort",
            "ObservabilityTracePort",
            "BankHandoffEnvelopePort",
            "ConfigurationSchemaPort",
            "HealthReadinessPort"
        ]

        for port_name in expected_ports:
            assert hasattr(ports, port_name), f"Port {port_name} not exported in app.ports"
            port_cls = getattr(ports, port_name)
            assert issubclass(port_cls, ABC), f"Port {port_name} must subclass abc.ABC"

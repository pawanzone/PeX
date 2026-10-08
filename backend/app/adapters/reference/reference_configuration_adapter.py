"""In-Memory Reference Configuration Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements ConfigurationSchemaPort.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.ports.configuration_port import ConfigurationSchemaPort
from app.schemas.contracts.configuration_schemas import (
    ValidatedSystemConfig,
    RailCutoffSchedule,
)


class InMemoryConfigurationAdapter(ConfigurationSchemaPort):
    """Hermetic reference implementation of ConfigurationSchemaPort."""

    def __init__(self, config: Optional[ValidatedSystemConfig] = None):
        self._config = config or ValidatedSystemConfig(
            environment="TEST_ONLY",
            service_name="pex_resolution_platform",
            version="0.2.0",
            rail_schedules=[
                RailCutoffSchedule(rail_code="FEDWIRE", currency="USD", operating_start_utc="00:00", cutoff_utc="22:00"),
                RailCutoffSchedule(rail_code="CHAPS", currency="GBP", operating_start_utc="06:00", cutoff_utc="17:00"),
                RailCutoffSchedule(rail_code="TARGET2", currency="EUR", operating_start_utc="07:00", cutoff_utc="18:00"),
                RailCutoffSchedule(rail_code="SWIFT_CBPR+", currency="USD", operating_start_utc="00:00", cutoff_utc="23:59")
            ],
            default_currency="USD",
            max_idempotency_lease_seconds=300,
            token_vault_key_id="REFERENCE_DEV_KEY_01",
            audit_chain_initial_seed="PEX_GENESIS_SEED_20261008",
            is_valid=True,
            validated_at=datetime.now(timezone.utc)
        )

    def load_configuration(
        self,
        config_dict: Optional[Dict[str, Any]] = None
    ) -> ValidatedSystemConfig:
        if config_dict:
            # Parse and validate
            schedules = [RailCutoffSchedule(**s) for s in config_dict.get("rail_schedules", [])]
            self._config = ValidatedSystemConfig(
                environment=config_dict.get("environment", "TEST_ONLY"),
                service_name=config_dict.get("service_name", "pex_resolution_platform"),
                version=config_dict.get("version", "0.2.0"),
                rail_schedules=schedules,
                default_currency=config_dict.get("default_currency", "USD"),
                is_valid=True,
                validated_at=datetime.now(timezone.utc)
            )
        return self._config

    def get_rail_schedule(
        self,
        rail_code: str
    ) -> Optional[Dict[str, Any]]:
        for s in self._config.rail_schedules:
            if s.rail_code == rail_code:
                return s.model_dump()
        return None

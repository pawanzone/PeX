"""Configuration Schema Port (SPI).

Defines the abstract interface for loading, validating, and retrieving system configuration
and published Bank Evidence Required configurations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.configuration_schemas import ValidatedSystemConfig
from app.schemas.contracts.evidence_config_schemas import BankEvidenceRequiredConfig


class ConfigurationSchemaPort(ABC):
    """Abstract port for configuration loading, validation, and dynamic evidence config management."""

    @abstractmethod
    def load_configuration(
        self,
        config_dict: Optional[Dict[str, Any]] = None
    ) -> ValidatedSystemConfig:
        """Loads and strictly validates system configuration parameters."""
        pass

    @abstractmethod
    def get_rail_schedule(
        self,
        rail_code: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves operating hours and cutoff for a clearing rail."""
        pass

    @abstractmethod
    def get_evidence_config(
        self,
        tenant_id: str,
        profile_id: str
    ) -> Optional[BankEvidenceRequiredConfig]:
        """Retrieves the published Bank Evidence Required configuration for (tenant_id, profile_id)."""
        pass

    @abstractmethod
    def publish_evidence_config(
        self,
        config: BankEvidenceRequiredConfig
    ) -> bool:
        """Publishes and validates a new Bank Evidence Required configuration."""
        pass

    @abstractmethod
    def list_evidence_configs(
        self,
        tenant_id: Optional[str] = None
    ) -> List[BankEvidenceRequiredConfig]:
        """Lists active published configurations."""
        pass

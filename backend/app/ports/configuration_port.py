"""Configuration Schema Port (SPI).

Defines the abstract interface for loading, validating, and retrieving system configuration.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.configuration_schemas import ValidatedSystemConfig


class ConfigurationSchemaPort(ABC):
    """Abstract port for configuration loading and validation."""

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

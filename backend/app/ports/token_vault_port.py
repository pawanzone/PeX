"""Secret Tokenization Vault Port (SPI).

Defines the abstract interface for isolating sensitive PII behind deterministic tokens
and enforcing zero PII exposure to AI models.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.token_vault_schemas import (
    TokenizedPayload,
    DetokenizationRequest,
)


class SecretTokenizationVaultPort(ABC):
    """Abstract port for PII tokenization and cryptographic isolation."""

    @abstractmethod
    def tokenize_value(
        self,
        raw_value: str,
        token_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TokenizedPayload:
        """Tokenizes sensitive data into a safe token for internal routing and AI context."""
        pass

    @abstractmethod
    def detokenize_value(
        self,
        request: DetokenizationRequest
    ) -> str:
        """Retrieves raw sensitive value for authorized bank execution gateway."""
        pass

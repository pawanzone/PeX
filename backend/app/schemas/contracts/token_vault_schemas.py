"""Secret Tokenization Vault & Zero-PII Boundary Schemas.

Defines the contract for isolating sensitive PII (names, IBANs, account numbers)
behind deterministic tokens. Zero raw PII exposed to AI model contexts.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TokenizationType(str):
    ACCOUNT = "ACCOUNT"
    IBAN = "IBAN"
    PARTY_NAME = "PARTY_NAME"
    TAX_ID = "TAX_ID"
    REMITTANCE = "REMITTANCE"


class TokenizedPayload(BaseModel):
    """Result of tokenizing a sensitive string or structured payload."""
    token: str                                       # e.g., "TOK-ACC-7F8A9B"
    token_type: str
    masked_value: str                                # e.g., "GB82****9876"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vault_key_id: str = "VAULT-KEY-REFERENCE"
    is_reversible_by_bank: bool = True
    is_safe_for_ai_context: bool = True


class DetokenizationRequest(BaseModel):
    """Request by authorized bank handoff gateway to retrieve real values."""
    token: str
    caller_role: str                                 # Must be authorized bank gateway role
    purpose: str = "BANK_EXECUTION_DISPATCH"

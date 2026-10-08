"""In-Memory Reference Secret Tokenization Vault Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements SecretTokenizationVaultPort using HMAC-SHA256 deterministic token mapping.
Enforces zero raw PII in internal context.
"""
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.ports.token_vault_port import SecretTokenizationVaultPort
from app.schemas.contracts.token_vault_schemas import (
    TokenizedPayload,
    DetokenizationRequest,
)


class InMemorySecretTokenizationVaultAdapter(SecretTokenizationVaultPort):
    """Hermetic reference implementation of SecretTokenizationVaultPort."""

    def __init__(self, secret_seed: str = "DEV_HMAC_SECRET_KEY_2026"):
        self._secret = secret_seed.encode()
        self._vault_store: Dict[str, str] = {} # token -> raw_value

    def tokenize_value(
        self,
        raw_value: str,
        token_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TokenizedPayload:
        now = datetime.now(timezone.utc)
        sig = hmac.new(self._secret, raw_value.encode(), hashlib.sha256).hexdigest()[:12].upper()
        prefix = "TOK-ACC" if token_type == "ACCOUNT" else ("TOK-IBAN" if token_type == "IBAN" else "TOK-PARTY")
        token = f"{prefix}-{sig}"
        self._vault_store[token] = raw_value

        # Masked string
        masked = f"{raw_value[:4]}****{raw_value[-4:]}" if len(raw_value) > 8 else "TOK****MASK"

        return TokenizedPayload(
            token=token,
            token_type=token_type,
            masked_value=masked,
            created_at=now,
            vault_key_id="REFERENCE_DEV_KEY_01"
        )

    def detokenize_value(
        self,
        request: DetokenizationRequest
    ) -> str:
        # Strict caller role enforcement
        if request.caller_role not in ["BANK_GATEWAY_OUTBOUND", "SWIFT_SETTLEMENT_CONNECTOR", "AUDIT_COMPLIANCE_OFFICER"]:
            raise PermissionError(f"Caller role {request.caller_role} is unauthorized to detokenize sensitive PII.")

        if request.token in self._vault_store:
            return self._vault_store[request.token]
        raise KeyError(f"Token {request.token} not found in token vault.")

"""Tokenization Vault & PII Isolation Boundary."""
import hashlib
import hmac
from typing import Dict, Tuple, Optional

class TokenVault:
    """
    Isolated Tokenization Vault.
    Maintains bidirectional pseudonym mapping.
    Zero-trust boundary: AI context receives ONLY TOK-* surrogates.
    """
    def __init__(self):
        self._raw_to_token: Dict[str, str] = {}
        self._token_to_raw: Dict[str, str] = {}

    def preload_tokens(self, token_records: list[dict]):
        for row in token_records:
            raw = row.get("raw_value") or row.get("original_value", "")
            token = row.get("token_value") or row.get("token", "")
            if raw and token:
                self._raw_to_token[raw] = token
                self._token_to_raw[token] = raw

    def tokenize(self, raw_value: str, token_type: str = "PARTY") -> str:
        if not raw_value:
            return ""
        
        clean_raw = raw_value.strip().replace(" ", "").upper()
        if clean_raw in self._raw_to_token:
            return self._raw_to_token[clean_raw]
        
        # Deterministic token generation
        # keyed (HMAC) so tokens cannot be recomputed from a list of names or IBANs without the vault key
        from app.config import settings
        h = hmac.new(str(settings.TOKEN_KEY).encode("utf-8"), clean_raw.encode("utf-8"), hashlib.sha256).hexdigest()[:12].upper()
        token = f"TOK-{token_type}-{h}"
        self._raw_to_token[clean_raw] = token
        self._token_to_raw[token] = clean_raw
        return token

    def detokenize(self, token: str) -> Optional[str]:
        return self._token_to_raw.get(token)

    def mask_identifier(self, identifier: str) -> str:
        """Helper for display masking e.g. GB82****765432."""
        clean = identifier.strip().replace(" ", "")
        if len(clean) <= 6:
            return clean
        return f"{clean[:4]}****{clean[-4:]}"

# Singleton instance
token_vault = TokenVault()

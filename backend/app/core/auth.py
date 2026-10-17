"""Authentication helpers: signed (HS256) session tokens for the demo persona login.

Production identity is the bank's IdP (OIDC/SSO) -- not built yet. Until then:
  * login is available ONLY when PEX_DEMO=true,
  * tokens are signed and expire; unsigned "pex-token-<id>" strings are rejected unless
    PEX_ALLOW_LEGACY_TOKENS=true (used by the test-suite only),
  * identity always comes from the token, never from the request body (except legacy/test mode).
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import HTTPException

from app.config import settings

_EPHEMERAL_SECRET = secrets.token_hex(32)


def _secret() -> bytes:
    return (settings.JWT_SECRET or _EPHEMERAL_SECRET).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(user_id: str, ttl_seconds: Optional[int] = None) -> str:
    ttl = ttl_seconds if ttl_seconds is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": user_id, "iat": now, "exp": now + ttl}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> Optional[str]:
    try:
        header, payload, sig = token.split(".")
        expected = _b64(hmac.new(_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return str(data.get("sub")) or None
    except Exception:
        return None


def resolve_user_id(authorization: Optional[str], fallback: Optional[str] = None, default: Optional[str] = None) -> str:
    """Returns the authenticated user id or raises 401.

    `fallback`/`default` (identity from a request body / implicit default) are honoured ONLY in
    legacy test mode; in normal operation identity must come from a valid signed token.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
        if token.startswith("pex-token-"):
            if settings.ALLOW_LEGACY_TOKENS:
                return token[len("pex-token-"):].strip()
            raise HTTPException(status_code=401, detail="Unsigned legacy token rejected")
        uid = verify_token(token)
        if uid:
            return uid
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if settings.ALLOW_LEGACY_TOKENS:
        if fallback:
            return fallback
        if default:
            return default
    raise HTTPException(status_code=401, detail="Authentication required")

"""Root conftest: test-mode security flags (must be set before the app/config is imported)."""
import os
os.environ.setdefault("PEX_DEMO", "true")
os.environ.setdefault("PEX_ALLOW_LEGACY_TOKENS", "true")      # unsigned legacy tokens accepted ONLY in tests
os.environ.setdefault("PEX_BANK_CALLBACK_SECRET", "test-bank-callback-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")

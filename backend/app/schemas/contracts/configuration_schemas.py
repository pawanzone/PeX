"""Configuration Schema Contract.

Defines the contract for validating system environment, clearing rail cutoff schedules,
and operational parameters at startup.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RailCutoffSchedule(BaseModel):
    """Cutoff and operating hours for a clearing rail."""
    rail_code: str                                   # "FEDWIRE", "CHAPS", "TARGET2", "BACS"
    currency: str                                    # "USD", "GBP", "EUR"
    operating_start_utc: str = "00:00"
    cutoff_utc: str = "22:00"
    settlement_cycle: str = "REAL_TIME_GROSS"
    is_active: bool = True


class ValidatedSystemConfig(BaseModel):
    """Immutable validated configuration tree."""
    environment: str = "TEST_ONLY"
    service_name: str = "pex_resolution_platform"
    version: str = "0.2.0"
    rail_schedules: List[RailCutoffSchedule] = Field(default_factory=list)
    default_currency: str = "USD"
    max_idempotency_lease_seconds: int = 300
    token_vault_key_id: str = "REFERENCE_DEV_KEY_01"
    audit_chain_initial_seed: str = "PEX_GENESIS_SEED_20261008"
    is_valid: bool = True
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

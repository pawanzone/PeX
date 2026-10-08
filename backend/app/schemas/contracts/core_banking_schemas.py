"""Core Banking DDA & Ledger Query Contract Schemas.

Defines the contract for querying real-time account balances, status, and freeze states.
Read-only queries; PeX never directly mutates core banking ledgers.
"""
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    DORMANT = "DORMANT"
    FROZEN_LEGAL = "FROZEN_LEGAL"
    FROZEN_SANCTIONS = "FROZEN_SANCTIONS"
    FROZEN_CREDIT = "FROZEN_CREDIT"
    SUSPENDED = "SUSPENDED"
    NOT_FOUND = "NOT_FOUND"


class AccountStateSnapshot(BaseModel):
    """Snapshot of account status and real-time ledger balance from Core Banking."""
    account_number_masked: str
    iban_masked: Optional[str] = None
    account_holder_name_masked: str
    currency: str
    status: AccountStatus
    available_balance: float
    posted_balance: float
    credit_limit: float = 0.0
    is_frozen: bool = False
    freeze_reason: Optional[str] = None
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_authoritative: bool = True
    core_system_id: str = "CORE_DDA_MASTER"

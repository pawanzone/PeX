"""Distributed Idempotency and Locking Contract Schemas.

Defines the contract for atomic lease acquisition, fencing tokens, and duplicate execution prevention.
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class LockStatus(str, Enum):
    ACQUIRED = "ACQUIRED"
    LOCKED_BY_OTHER = "LOCKED_BY_OTHER"
    ALREADY_EXECUTED = "ALREADY_EXECUTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class LockAcquisitionResult(BaseModel):
    """Result of attempting to acquire an atomic idempotency lock."""
    idempotency_key: str
    status: LockStatus
    holder_id: Optional[str] = None
    fencing_token: int = 0
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    existing_execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

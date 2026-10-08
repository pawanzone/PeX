"""Distributed Idempotency & Locking Port (SPI).

Defines the abstract interface for acquiring atomic leases, enforcing duplicate prevention,
and recording execution outcomes.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.idempotency_schemas import (
    LockAcquisitionResult,
)


class DistributedIdempotencyPort(ABC):
    """Abstract port for distributed locking and idempotency tracking."""

    @abstractmethod
    def acquire_lock(
        self,
        idempotency_key: str,
        holder_id: str,
        lease_duration_ms: int = 30000
    ) -> LockAcquisitionResult:
        """Atomically acquires an idempotency lock for the given key."""
        pass

    @abstractmethod
    def release_lock(
        self,
        idempotency_key: str,
        holder_id: str
    ) -> bool:
        """Releases the lock on failure or normal completion."""
        pass

    @abstractmethod
    def record_execution(
        self,
        idempotency_key: str,
        execution_result: Dict[str, Any]
    ) -> bool:
        """Permanently records the execution result to prevent replay."""
        pass

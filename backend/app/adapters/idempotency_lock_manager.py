"""Provider-Neutral Idempotency Lock Manager Port and In-Memory Adapter for PR-08.

Enforces concurrency-safe atomic locking and duplicate execution prevention for queue recovery.
Addresses race conditions where concurrent workers could attempt simultaneous re-enqueue or replay.

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md
"""
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field


class LockRecord(BaseModel):
    """Metadata representing an active or acquired idempotency lock."""
    lock_key: str
    owner: str
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_active: bool = True
    execution_result_hash: Optional[str] = None


class IdempotencyLockManagerPort(ABC):
    """Abstract port for managing atomic concurrency locks and duplicate execution prevention."""

    @abstractmethod
    def acquire_lock(self, key: str, ttl_seconds: int = 300, owner: str = "PEX_RECOVERY_WORKER") -> bool:
        """Atomically acquires an exclusive lock for the given idempotency key.
        
        Returns True if acquired, False if lock is already held by another active worker.
        """
        pass

    @abstractmethod
    def release_lock(self, key: str, owner: str = "PEX_RECOVERY_WORKER") -> bool:
        """Releases the lock held by the specified owner."""
        pass

    @abstractmethod
    def is_locked(self, key: str) -> bool:
        """Checks if a valid, unexpired lock is currently active for the key."""
        pass

    @abstractmethod
    def record_execution(self, key: str, result_hash: str) -> bool:
        """Permanently records that a recovery action for this key has completed."""
        pass

    @abstractmethod
    def is_already_executed(self, key: str) -> bool:
        """Checks if the recovery action for this key has already been completed."""
        pass


class InMemoryIdempotencyLockManager(IdempotencyLockManagerPort):
    """Thread-safe, in-memory implementation of IdempotencyLockManagerPort with atomic CAS semantics.
    
    Provides Level-1 validation of race-condition safety.
    Production deployments substitute distributed Redis/DynamoDB/Zookeeper lock managers (BANK_CONFIG_REQUIRED).
    """

    def __init__(self):
        self._mutex = threading.Lock()
        self._locks: Dict[str, LockRecord] = {}
        self._completed_executions: Dict[str, Tuple[str, datetime]] = {}

    def acquire_lock(self, key: str, ttl_seconds: int = 300, owner: str = "PEX_RECOVERY_WORKER") -> bool:
        with self._mutex:
            now = datetime.now(timezone.utc)
            # Check if already permanently executed
            if key in self._completed_executions:
                return False

            # Check existing lock
            if key in self._locks:
                existing = self._locks[key]
                if existing.is_active and existing.expires_at > now:
                    if existing.owner == owner:
                        # Re-entrant by same owner
                        return True
                    return False

            # Acquire new atomic lock
            expires = now + timedelta(seconds=ttl_seconds)
            self._locks[key] = LockRecord(
                lock_key=key,
                owner=owner,
                acquired_at=now,
                expires_at=expires,
                is_active=True
            )
            return True

    def release_lock(self, key: str, owner: str = "PEX_RECOVERY_WORKER") -> bool:
        with self._mutex:
            if key in self._locks:
                existing = self._locks[key]
                if existing.owner == owner:
                    existing.is_active = False
                    del self._locks[key]
                    return True
            return False

    def is_locked(self, key: str) -> bool:
        with self._mutex:
            now = datetime.now(timezone.utc)
            if key in self._locks:
                existing = self._locks[key]
                return existing.is_active and existing.expires_at > now
            return False

    def record_execution(self, key: str, result_hash: str) -> bool:
        with self._mutex:
            now = datetime.now(timezone.utc)
            self._completed_executions[key] = (result_hash, now)
            if key in self._locks:
                del self._locks[key]
            return True

    def is_already_executed(self, key: str) -> bool:
        with self._mutex:
            return key in self._completed_executions

    def clear(self):
        """Resets all internal locks (testing only)."""
        with self._mutex:
            self._locks.clear()
            self._completed_executions.clear()


# Global singleton instance for application use
idempotency_lock_manager = InMemoryIdempotencyLockManager()

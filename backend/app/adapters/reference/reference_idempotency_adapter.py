"""In-Memory Reference Idempotency Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements DistributedIdempotencyPort using thread-safe in-memory dictionaries.
"""
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from app.ports.idempotency_port import DistributedIdempotencyPort
from app.schemas.contracts.idempotency_schemas import (
    LockStatus,
    LockAcquisitionResult,
)


class InMemoryIdempotencyAdapter(DistributedIdempotencyPort):
    """Thread-safe in-memory reference implementation of DistributedIdempotencyPort."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_locks: Dict[str, Dict[str, Any]] = {}
        self._execution_history: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def acquire_lock(
        self,
        idempotency_key: str,
        holder_id: str,
        lease_duration_ms: int = 30000
    ) -> LockAcquisitionResult:
        with self._lock:
            now = datetime.now(timezone.utc)

            # 1. Check if already permanently executed
            if idempotency_key in self._execution_history:
                return LockAcquisitionResult(
                    idempotency_key=idempotency_key,
                    status=LockStatus.ALREADY_EXECUTED,
                    holder_id=holder_id,
                    existing_execution_result=self._execution_history[idempotency_key]
                )

            # 2. Check active lock
            if idempotency_key in self._active_locks:
                current_lock = self._active_locks[idempotency_key]
                if now < current_lock["expires_at"] and current_lock["holder_id"] != holder_id:
                    return LockAcquisitionResult(
                        idempotency_key=idempotency_key,
                        status=LockStatus.LOCKED_BY_OTHER,
                        holder_id=current_lock["holder_id"],
                        expires_at=current_lock["expires_at"]
                    )

            # 3. Grant lock
            self._counter += 1
            fencing_token = self._counter
            expires_at = now + timedelta(milliseconds=lease_duration_ms)
            self._active_locks[idempotency_key] = {
                "holder_id": holder_id,
                "fencing_token": fencing_token,
                "acquired_at": now,
                "expires_at": expires_at
            }

            return LockAcquisitionResult(
                idempotency_key=idempotency_key,
                status=LockStatus.ACQUIRED,
                holder_id=holder_id,
                fencing_token=fencing_token,
                acquired_at=now,
                expires_at=expires_at
            )

    def release_lock(
        self,
        idempotency_key: str,
        holder_id: str
    ) -> bool:
        with self._lock:
            if idempotency_key in self._active_locks:
                if self._active_locks[idempotency_key]["holder_id"] == holder_id:
                    del self._active_locks[idempotency_key]
                    return True
            return False

    def record_execution(
        self,
        idempotency_key: str,
        execution_result: Dict[str, Any]
    ) -> bool:
        with self._lock:
            self._execution_history[idempotency_key] = execution_result
            if idempotency_key in self._active_locks:
                del self._active_locks[idempotency_key]
            return True

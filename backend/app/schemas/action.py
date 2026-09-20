"""Governed Action Execution & Delivery Receipts."""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.recommendation import ActionType

class ActionStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"

class GovernedActionContract(BaseModel):
    action_id: str
    case_id: str
    approval_ids: list[str]
    action_type: ActionType
    target_system: str = "SIMULATED_BANK_PAYMENT_HUB"
    idempotency_key: str
    dispatch_payload: Dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    dispatched_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None

class DeliveryReceipt(BaseModel):
    receipt_id: str
    action_id: str
    case_id: str
    bank_ack_reference: str
    status: str = "SETTLED_CONFIRMED"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any]

"""Pydantic schemas and contracts for Governed Straight-Through Processing (STP)."""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class STPMode(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"             # Zero-touch auto-settlement (<$10k, >98% conf, syntax only)
    ONE_CLICK_BATCH = "ONE_CLICK_BATCH"   # 1-click supervised batch release (<$25k, >95% conf)
    MANUAL_GATED = "MANUAL_GATED"         # Standard HITL / Dual-Auth manual review required

class STPEligibilityItem(BaseModel):
    case_id: str
    payment_id: str
    amount: float
    currency: str
    domain: str
    profile: str
    ai_confidence: Optional[float] = None
    eligible: bool
    mode: STPMode
    reason: str
    matching_rule_id: Optional[str] = None
    matching_rule_name: Optional[str] = None
    proposed_repair_summary: Optional[str] = None

class BatchSTPRequest(BaseModel):
    case_ids: List[str]
    approver_id: str
    approver_name: str
    approver_role: str
    comments: Optional[str] = "Governed 1-click fast-lane batch settlement executed."

class SettledCaseSummary(BaseModel):
    case_id: str
    payment_id: str
    amount: float
    currency: str
    action_id: str
    receipt_id: str
    status: str = "SETTLED"

class BatchSTPResponse(BaseModel):
    batch_id: str
    total_requested: int
    processed_count: int
    failed_count: int
    settled_cases: List[SettledCaseSummary]
    total_dollar_volume: float
    executed_by: str
    timestamp: str
    message: str

class STPTelemetryResponse(BaseModel):
    total_cases: int
    settled_cases: int
    overall_stp_rate_pct: float
    fast_lane_eligible_count: int
    fast_lane_eligible_volume: float
    autonomous_stp_count: int
    batch_fast_lane_count: int
    avg_resolution_seconds_stp: float
    avg_resolution_seconds_manual: float
    time_savings_hours: float
    domain_stp_rates: Dict[str, float]
    active_stp_rules: List[Dict[str, Any]]

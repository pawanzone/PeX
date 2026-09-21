"""REST API Endpoints for Governed Straight-Through Processing (STP) & Fast-Lane."""
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.stp import (
    STPEligibilityItem,
    BatchSTPRequest,
    BatchSTPResponse,
    STPTelemetryResponse,
)
from app.services.stp_engine import stp_engine
from app.services.data_loader import repo

router = APIRouter(prefix="/stp", tags=["Governed Straight-Through Processing (STP)"])

@router.get("/eligible", response_model=List[STPEligibilityItem])
def get_eligible_stp_cases():
    """Returns all open payment exception cases currently qualified for STP / Fast-Lane."""
    return stp_engine.get_eligible_cases()

@router.get("/telemetry", response_model=STPTelemetryResponse)
def get_stp_telemetry():
    """Returns live STP adoption metrics, processing velocity, and operational savings."""
    return stp_engine.get_stp_telemetry()

@router.post("/batch-release", response_model=BatchSTPResponse, status_code=status.HTTP_200_OK)
def execute_batch_fast_lane(payload: BatchSTPRequest):
    """Approver executes 1-click batch settlement release for selected fast-lane cases."""
    if not payload.case_ids:
        raise HTTPException(status_code=400, detail="At least one case_id must be provided for batch release")

    # Enforce Approver authority (Makers cannot authorize batch release)
    if payload.approver_role == "OPERATOR":
        raise HTTPException(
            status_code=403,
            detail="Segregation of Duties Violation: Operator (Maker) cannot authorize batch settlement release. Operations Approver or Admin required."
        )

    return stp_engine.execute_batch_fast_lane_release(payload)

@router.post("/cases/{case_id}/auto-execute", response_model=Dict[str, Any])
def execute_case_autonomous_stp(case_id: str):
    """Executes immediate zero-touch autonomous STP repair and settlement for an eligible micro-case."""
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    try:
        return stp_engine.execute_autonomous_stp(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

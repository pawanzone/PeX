"""REST API Endpoints for Governed Straight-Through Processing (STP) & Fast-Lane."""
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.core.auth import resolve_user_id
from app.core.security import get_persona

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
def execute_batch_fast_lane(payload: BatchSTPRequest, authorization: Optional[str] = Header(None)):
    """Approver executes 1-click batch settlement release for selected fast-lane cases.

    Approver identity, name and role come from the signed token, never from the request body.
    """
    if not payload.case_ids:
        raise HTTPException(status_code=400, detail="At least one case_id must be provided for batch release")

    uid = resolve_user_id(authorization, fallback=payload.approver_id)
    persona = get_persona(uid)
    if persona is None:
        raise HTTPException(status_code=403, detail=f"Unknown approver '{uid}'")
    role = persona.role.value if hasattr(persona.role, "value") else str(persona.role)

    # Enforce Approver authority (Makers cannot authorize batch release)
    if role == "OPERATOR":
        raise HTTPException(
            status_code=403,
            detail="Segregation of Duties Violation: Operator (Maker) cannot authorize batch settlement release. Operations Approver or Admin required."
        )

    payload = payload.model_copy(update={"approver_id": persona.user_id, "approver_name": persona.name, "approver_role": role})
    return stp_engine.execute_batch_fast_lane_release(payload)

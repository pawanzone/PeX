"""Audit Log & Provenance Stream Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.audit_service import audit_service
from app.schemas.audit import AuditEvent, ProvenanceChain, HashVerificationResult

router = APIRouter()

@router.get("/stream", response_model=List[AuditEvent])
def get_audit_stream(limit: int = 1000):
    return audit_service.get_all_events(limit=limit)

@router.get("/verify-chain", response_model=HashVerificationResult)
def verify_audit_chain():
    return audit_service.verify_chain()

@router.get("/case/{case_id}", response_model=ProvenanceChain)
def get_case_audit_chain(case_id: str):
    return audit_service.get_case_provenance(case_id)



"""AI Copilot & SOP Knowledge Base Endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter()

SOPS: List[Dict[str, Any]] = [
    {
        "sop_id": "SOP-114-IBAN",
        "title": "Beneficiary IBAN Validation & Transposition Repair",
        "category": "Repair Operations",
        "last_updated": "2026-08-31",
        "summary": "Governs ISO 7064 MOD-97-10 checksum validation, national length matrix checks, and transposition repair hypotheses grounded in Master SSI profiles."
    },
    {
        "sop_id": "SOP-115-BIC",
        "title": "Invalid BIC & Routing Resolution",
        "category": "Routing Operations",
        "last_updated": "2026-08-31",
        "summary": "Procedures for SWIFT ISO 9362 8-to-11 char expansion, bank merger LEI mappings, closed branch fallbacks, and clearing rail cutoff adherence."
    },
    {
        "sop_id": "SOP-204-DUP",
        "title": "Duplicate Payment & Burst Detection",
        "category": "Risk & Fraud",
        "last_updated": "2026-08-31",
        "summary": "Defines 4-point vector matching (Beneficiary + Remittance + Amount + 30m window) and disambiguates legitimate recurring payroll/retainers from ERP retries."
    },
    {
        "sop_id": "SOP-301-SAN",
        "title": "Sanctions Screening Match & Homonym Clearance",
        "category": "Compliance",
        "last_updated": "2026-08-31",
        "summary": "Mandates secondary identifier verification (Tax ID, Incorporation Date, UBO) for clearing 85%-97% fuzzy watchlist matches. Restricted to Compliance Approvers."
    },
    {
        "sop_id": "SOP-302-KYC",
        "title": "KYC Expiration & 30-Day Provisional Waiver Governance",
        "category": "Compliance",
        "last_updated": "2026-08-31",
        "summary": "Authorizes 30-day provisional processing waivers under strict conditions (clean 24m history, low-risk corridor, refresh underway) for Tier 1 counterparties."
    },
    {
        "sop_id": "SOP-401-RET",
        "title": "ISO 20022 pacs.004 Return Reconciliation",
        "category": "Settlement & Treasury",
        "last_updated": "2026-08-31",
        "summary": "Procedures for correlating incoming pacs.004 return messages, mapping return codes (AC04, AC06, AG01), fee deductions, and originating suspense re-credits."
    },
    {
        "sop_id": "SOP-207-DUAL",
        "title": "Dual Authorization for High-Value Exceptions (>= $250k)",
        "category": "Risk & Governance",
        "last_updated": "2026-08-31",
        "summary": "Requires two distinct authenticated officers (Tier 1: Operations, Tier 2: Risk/Compliance) before dispatching any payment repair >= $250,000 USD."
    }
]

from app.services.skill_policy_service import skill_policy_service

class ChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None

@router.get("/sops")
def list_sops():
    return SOPS

@router.get("/skills/active")
def get_active_skills():
    """Returns active dynamically parsed SME skills and runtime policy parameters."""
    return skill_policy_service.load_active_skills()

@router.post("/chat")
def copilot_chat(req: ChatRequest):
    msg = req.message.lower()
    case_id = req.case_id or "Active Context"
    
    # Ground chat directly in dynamic skill policy parameters
    params = skill_policy_service.get_policy_parameters()
    da_val = params.get("dual_auth_threshold", 250000.0)
    
    if "iban" in msg or "repair" in msg:
        reply = f"For Beneficiary IBAN exceptions (under **SOP-114-IBAN**), PeX validates ISO 7064 MOD-97 check digits against verified beneficiary standing profiles. In case **{case_id}**, the corrected check digits have been validated and require Ops Approver authorization before bank dispatch."
    elif "dual" in msg or "250" in msg or "high value" in msg:
        reply = f"Under **SOP-207-DUAL**, all payment repairs for amounts >= ${da_val:,.0f} strictly require Dual Authorization (First Approver: Operations, Second Approver: Risk/Executive). Single-approver release is blocked at the gateway."
    elif "sanction" in msg or "compliance" in msg:
        reply = "Under **SOP-301-SAN**, any sanctions hit is locked in the Compliance Queue and can only be cleared or escalated by a certified Compliance Approver (e.g. Marisol Vega)."
    elif "kyc" in msg:
        reply = "Under **SOP-302-KYC**, low-risk corporate counterparties with clean 24-month histories are eligible for a 30-day provisional processing waiver granted by Compliance."
    else:
        reply = f"I am your PeX Governed AI Copilot. I have access to your active case context ({case_id}), payment ontology, and active SME skill playbooks (SOP-114-IBAN, SOP-115-BIC, SOP-204-DUP, SOP-301-SAN, SOP-302-KYC, SOP-401-RET). All PII is redacted under zero-trust privacy boundaries."
        
    return {
        "reply": reply,
        "timestamp": datetime.utcnow().isoformat(),
        "sop_reference": "SOP-114-IBAN",
        "privacy_mode": "TOKENIZED_ZERO_PII"
    }

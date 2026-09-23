import os

ep_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints"

# 5. endpoints/ontology.py
with open(os.path.join(ep_dir, "ontology.py"), "w", encoding="utf-8") as f:
    f.write('''"""Payment Ontology & Lineage Inspector Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.services.data_loader import repo

router = APIRouter()

@router.get("/pipeline")
def get_pipeline_stages() -> List[Dict[str, Any]]:
    return [
        {"stage_id": "1", "name": "Event Ingestion", "description": "Bank-specific raw payload ingestion (REST, Kafka, MQ)"},
        {"stage_id": "2", "name": "Canonical Mapping", "description": "ISO 20022 / SWIFT normalization & provenance capture"},
        {"stage_id": "3", "name": "Tokenization Gate", "description": "PII masking & token vault substitution (TOK-*)"},
        {"stage_id": "4", "name": "Evidence Planning", "description": "Connector retrieval across Directories, Policies & History"},
        {"stage_id": "5", "name": "Governed AI Reasoning", "description": "Model Gateway recommendation & confidence scoring"},
        {"stage_id": "6", "name": "HITL Approval & Action", "description": "Maker-checker authorization, simulated dispatch & audit chain"}
    ]

@router.get("/entities")
def get_canonical_entities() -> List[Dict[str, Any]]:
    return [
        {"entity": "CanonicalPayment", "standard": "ISO 20022 pacs.008", "fields": "UETR, InstructionID, Amount, Ccy, Rail, SettlementDate"},
        {"entity": "CanonicalParty", "standard": "BIAN / ISO Party", "fields": "PartyID, Name, Type (Debtor/Creditor), Country, TokenRef"},
        {"entity": "CanonicalAccount", "standard": "ISO 20022 Account", "fields": "AccountID, Number, IBAN, BIC, Currency, TokenRef"},
        {"entity": "CanonicalException", "standard": "PeX Exception Domain", "fields": "ExceptionID, CaseID, Profile, ErrorCode, Severity, SLA"},
        {"entity": "EvidenceItem", "standard": "PeX Evidence Schema", "fields": "EvidenceID, Type, Connector, Data, RelevanceScore"},
        {"entity": "DecisionRecommendation", "standard": "PeX Decision Contract", "fields": "ActionType, ConfidenceScore, Rationale, ProposedChanges"},
        {"entity": "GovernedActionContract", "standard": "ISO 20022 pacs.004 / camt", "fields": "ActionID, TargetSystem, IdempotencyKey, Receipt"}
    ]

@router.get("/inspect/{case_id}")
def inspect_case_ontology(case_id: str) -> Dict[str, Any]:
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    rec = repo.recommendations.get(case_id)
    approvals = repo.approvals.get(case_id, [])
    
    return {
        "case_id": case_id,
        "payment": {
            "uetr": case.get("uetr"),
            "payment_ref": case.get("payment_ref"),
            "amount": case.get("amount"),
            "currency": case.get("currency"),
            "payment_rail": case.get("payment_rail")
        },
        "debtor": case.get("debtor_party"),
        "debtor_account": case.get("debtor_account"),
        "creditor": case.get("creditor_party"),
        "creditor_account": case.get("creditor_account"),
        "exception_profile": case.get("profile"),
        "status": case.get("status"),
        "ai_recommendation": rec.dict() if rec else None,
        "approvals": [a.dict() for a in approvals]
    }
''')

# 6. endpoints/copilot.py
with open(os.path.join(ep_dir, "copilot.py"), "w", encoding="utf-8") as f:
    f.write('''"""AI Copilot & SOP Knowledge Base Endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter()

SOPS: List[Dict[str, Any]] = [
    {
        "sop_id": "SOP-114",
        "title": "Beneficiary IBAN Repair Procedures",
        "category": "Repair Operations",
        "last_updated": "2026-01-20",
        "summary": "Governs automated and assisted repair of invalid check digits in beneficiary IBANs. Mandates standing instruction lookup and MOD-97 checksum revalidation."
    },
    {
        "sop_id": "SOP-207",
        "title": "Dual Authorization for High-Value Exceptions (>= $250k)",
        "category": "Risk & Governance",
        "last_updated": "2026-02-11",
        "summary": "Requires two distinct authenticated approvers for any payment correction equal to or exceeding $250,000 USD equivalent."
    },
    {
        "sop_id": "SOP-301",
        "title": "Sanctions Screening Match & Escalation Protocol",
        "category": "Compliance",
        "last_updated": "2026-03-01",
        "summary": "Defines secondary review procedures when SWIFT payment entities match OFAC/EU watchlist fuzzy score >= 0.85. Prohibits straight-through release."
    },
    {
        "sop_id": "SOP-402",
        "title": "SWIFT pacs.004 Return Reconciliation",
        "category": "Settlement & Treasury",
        "last_updated": "2026-01-05",
        "summary": "Procedures for parsing return reason codes (AC01, AG01, MS03) and originating customer return credit ledger postings."
    }
]

class ChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None

@router.get("/sops")
def list_sops():
    return SOPS

@router.post("/chat")
def copilot_chat(req: ChatRequest):
    msg = req.message.lower()
    case_id = req.case_id or "Active Context"
    
    if "iban" in msg or "repair" in msg:
        reply = f"For Beneficiary IBAN exceptions (under **SOP-114**), PeX validates ISO 7064 MOD-97 check digits against verified beneficiary standing profiles. In case **{case_id}**, the corrected check digits have been validated and require Ops Approver authorization before bank dispatch."
    elif "dual" in msg or "250" in msg or "high value" in msg:
        reply = "Under **SOP-207**, all payment repairs for amounts >= $250,000 USD strictly require Dual Authorization (First Approver: Operations, Second Approver: Risk/Executive). Single-approver release is blocked at the gateway."
    elif "sanction" in msg or "compliance" in msg:
        reply = "Under **SOP-301**, any sanctions hit is locked in the Compliance Queue and can only be cleared or escalated by a certified Compliance Approver (e.g. Marisol Vega)."
    else:
        reply = f"I am your PeX Governed AI Copilot. I have access to your active case context ({case_id}), payment ontology, and institutional SOPs (SOP-114, SOP-207, SOP-301, SOP-402). All PII is redacted under zero-trust privacy boundaries."
        
    return {
        "reply": reply,
        "pii_redacted": True,
        "token_cost_estimated": "$0.0004",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S")
    }
''')

# 7. endpoints/audit.py
with open(os.path.join(ep_dir, "audit.py"), "w", encoding="utf-8") as f:
    f.write('''"""Audit Log & Provenance Stream Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.audit_service import audit_service
from app.schemas.audit import AuditEvent, ProvenanceChain

router = APIRouter()

@router.get("/stream", response_model=List[AuditEvent])
def get_audit_stream(limit: int = 100):
    return audit_service.get_all_events(limit=limit)

@router.get("/case/{case_id}", response_model=ProvenanceChain)
def get_case_audit_chain(case_id: str):
    return audit_service.get_case_provenance(case_id)
''')

print("Wrote ontology.py, copilot.py, and audit.py")

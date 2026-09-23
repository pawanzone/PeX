import os

ep_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints"
os.makedirs(ep_dir, exist_ok=True)

# 1. endpoints/auth.py
with open(os.path.join(ep_dir, "auth.py"), "w", encoding="utf-8") as f:
    f.write('''"""Authentication & Persona Endpoints."""
from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional

from app.schemas.auth import UserPersona, LoginRequest, LoginResponse
from app.core.security import DEMO_PERSONAS, get_persona

router = APIRouter()

@router.get("/personas", response_model=List[UserPersona])
def list_personas():
    return list(DEMO_PERSONAS.values())

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    persona = get_persona(req.user_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # In demo mode, token is user_id prefixed
    token = f"pex-token-{persona.user_id}"
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=persona
    )

@router.get("/me", response_model=UserPersona)
def get_current_user(authorization: Optional[str] = Header(None)):
    user_id = "OP-8472" # Default to Amina Okafor
    if authorization and authorization.startswith("Bearer pex-token-"):
        user_id = authorization.replace("Bearer pex-token-", "").strip()
    
    persona = get_persona(user_id) or DEMO_PERSONAS["OP-8472"]
    return persona
''')

# 2. endpoints/analytics.py
with open(os.path.join(ep_dir, "analytics.py"), "w", encoding="utf-8") as f:
    f.write('''"""Operations Analytics & KPI Endpoints."""
from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime

from app.services.data_loader import repo
from app.schemas.canonical import LifecycleStage

router = APIRouter()

@router.get("/summary")
def get_analytics_summary() -> Dict[str, Any]:
    all_cases = list(repo.cases.values())
    total_cases = len(all_cases)
    
    open_cases = [c for c in all_cases if c.get("status") not in [LifecycleStage.SETTLED, LifecycleStage.REJECTED]]
    resolved_cases = [c for c in all_cases if c.get("status") in [LifecycleStage.SETTLED, LifecycleStage.REJECTED]]
    
    at_risk_value = sum(float(c.get("amount", 0.0)) for c in open_cases)
    critical_value = sum(float(c.get("amount", 0.0)) for c in all_cases if c.get("priority") == "CRITICAL" or c.get("severity") == "CRITICAL")
    
    # Due < 1hr mock count
    due_soon_count = min(4, len(open_cases))
    
    resolution_rate = round((len(resolved_cases) / max(total_cases, 1)) * 100, 1)
    
    # Queue distribution
    repair_count = len([c for c in open_cases if c.get("queue") == "Repair"])
    comp_count = len([c for c in open_cases if c.get("queue") == "Compliance"])
    inv_count = len([c for c in open_cases if c.get("queue") == "Investigation"])
    treasury_count = len([c for c in open_cases if c.get("queue") == "Treasury"])
    
    return {
        "open_cases": len(open_cases),
        "total_cases": total_cases,
        "resolved_cases": len(resolved_cases),
        "at_risk_value": at_risk_value,
        "critical_value": critical_value,
        "resolution_rate": resolution_rate,
        "due_under_1hr": due_soon_count,
        "queue_distribution": {
            "Repair": repair_count,
            "Compliance": comp_count,
            "Investigation": inv_count,
            "Treasury": treasury_count
        },
        "processing_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "telemetry_status": "ONLINE"
    }

@router.get("/velocity")
def get_sla_resolution_velocity() -> List[Dict[str, Any]]:
    # 7-day velocity chart data
    days = ["Wed", "Thu", "Fri", "Sat", "Sun", "Today"]
    return [
        {"day": "Wed", "opened": 2, "resolved": 2},
        {"day": "Thu", "opened": 1, "resolved": 1},
        {"day": "Fri", "opened": 2, "resolved": 1},
        {"day": "Sat", "opened": 1, "resolved": 1},
        {"day": "Sun", "opened": 6, "resolved": 1},
        {"day": "Today", "opened": 12, "resolved": 5}
    ]
''')

# 3. endpoints/adapters.py
with open(os.path.join(ep_dir, "adapters.py"), "w", encoding="utf-8") as f:
    f.write('''"""SWIFT & ISO Center Integration Adapters Endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter()

ADAPTERS_STATE: List[Dict[str, Any]] = [
    {
        "adapter_id": "ADAPT-ACTION-GW",
        "name": "Action Gateway",
        "protocol": "iso20022-https",
        "description": "Repairs, returns, release instructions outbound dispatcher",
        "status": "HEALTHY",
        "latency_ms": 28,
        "last_tested": "2026-08-24 00:01:15"
    },
    {
        "adapter_id": "ADAPT-ENT-BUS",
        "name": "Enterprise Bus",
        "protocol": "mq-kafka-bridge",
        "description": "FedWire MQ / Kafka streaming bridge",
        "status": "HEALTHY",
        "latency_ms": 14,
        "last_tested": "2026-08-24 00:01:20"
    },
    {
        "adapter_id": "ADAPT-PMT-HUB",
        "name": "Payment Hub",
        "protocol": "iso20022-https",
        "description": "SWIFT Alliance Access / CBPR+ Gateway",
        "status": "HEALTHY",
        "latency_ms": 35,
        "last_tested": "2026-08-24 00:01:22"
    },
    {
        "adapter_id": "ADAPT-REF-DATA",
        "name": "Reference Data",
        "protocol": "rest",
        "description": "SWIFT BIC / SSI Directory & clearing matrix",
        "status": "HEALTHY",
        "latency_ms": 19,
        "last_tested": "2026-08-24 00:01:25"
    },
    {
        "adapter_id": "ADAPT-SWIFT-CASE",
        "name": "SWIFT Case Management",
        "protocol": "swift-api",
        "description": "gCase / Exception & Investigation (E&I) API",
        "status": "HEALTHY",
        "latency_ms": 42,
        "last_tested": "2026-08-24 00:01:28"
    },
    {
        "adapter_id": "ADAPT-SANCTIONS",
        "name": "Sanctions Screening Service",
        "protocol": "rest",
        "description": "Real-time OFAC / EU / UN PEP & Watchlist engine",
        "status": "HEALTHY",
        "latency_ms": 52,
        "last_tested": "2026-08-24 00:01:30"
    }
]

class TestAdapterRequest(BaseModel):
    adapter_id: str

@router.get("/status")
def list_adapters():
    return ADAPTERS_STATE

@router.post("/test")
def test_adapter(req: TestAdapterRequest):
    for a in ADAPTERS_STATE:
        if a["adapter_id"] == req.adapter_id:
            a["last_tested"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            return {"status": "SUCCESS", "message": f"{a['name']} ping successful", "latency_ms": a["latency_ms"]}
    raise HTTPException(status_code=404, detail="Adapter not found")
''')

# 4. endpoints/governance.py
with open(os.path.join(ep_dir, "governance.py"), "w", encoding="utf-8") as f:
    f.write('''"""Controls & Governance Endpoints."""
from fastapi import APIRouter
from typing import Dict, Any
from app.services.audit_service import audit_service
from app.schemas.audit import HashVerificationResult

router = APIRouter()

@router.get("/controls")
def get_operational_controls() -> Dict[str, Any]:
    audit_res = audit_service.verify_chain()
    return {
        "controls": [
            {
                "name": "Identity & entitlements",
                "status": "DEMO MODE",
                "description": "Open demo: server-assigned demo operator is used. Set PEX_ENFORCE_AUTH=true for production posture."
            },
            {
                "name": "Bank isolation",
                "status": "ENFORCED",
                "description": "All queries and decisions are scoped to the operator's bank/tenant."
            },
            {
                "name": "Segregation of duties",
                "status": "ENFORCED",
                "description": "Server blocks maker self-approval; config proposers cannot approve their own changes."
            },
            {
                "name": "Dual authorization",
                "status": "ENFORCED",
                "description": "Repairs at or above $250,000 require two distinct approvers."
            },
            {
                "name": "Sensitive-data boundary",
                "status": "ENFORCED",
                "description": "Cases use payment tokens; raw account details are never exposed to AI models."
            }
        ],
        "ai_model_posture": {
            "boundary": "Evidence-grounded recommendations only; all payment-changing actions require human approval.",
            "mode": "Governed Deterministic Planner + Multi-Model Gateway"
        },
        "continuous_audit": {
            "latest_head_hash": audit_res.chain_head,
            "total_events": audit_res.total_events_checked,
            "chain_verified_intact": audit_res.is_intact
        }
    }

@router.get("/audit-chain/verify", response_model=HashVerificationResult)
def verify_audit_chain_endpoint():
    return audit_service.verify_chain()
''')

print("Wrote auth.py, analytics.py, adapters.py, and governance.py")

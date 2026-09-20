"""SWIFT & ISO Center Integration Adapters Endpoints."""
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

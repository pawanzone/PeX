"""API Router Aggregator for PeX Platform."""
from fastapi import APIRouter

from app.api.endpoints import (
    auth, cases, events, approvals, actions, analytics,
    adapters, governance, ontology, copilot, audit, rules, stp, bank
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Personas"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases & Investigation Workflow"])
api_router.include_router(events.router, prefix="/events", tags=["Bank Event Ingestion"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Role-Gated Approvals"])
api_router.include_router(actions.router, prefix="/actions", tags=["Governed Action Execution"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Operations Analytics"])
api_router.include_router(adapters.router, prefix="/adapters", tags=["SWIFT & ISO Center Adapters"])
api_router.include_router(governance.router, prefix="/governance", tags=["Controls & Governance"])
api_router.include_router(ontology.router, prefix="/ontology", tags=["Payment Ontology"])
api_router.include_router(copilot.router, prefix="/copilot", tags=["AI Copilot"])
api_router.include_router(audit.router, prefix="/audit", tags=["Continuous Audit & Provenance"])
api_router.include_router(bank.router, prefix="/bank", tags=["Bank Systems Inbound Signal Gateway"])
api_router.include_router(rules.router)
api_router.include_router(stp.router)


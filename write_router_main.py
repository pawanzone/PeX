import os

api_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api"
app_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app"

# 1. api/router.py
with open(os.path.join(api_dir, "router.py"), "w", encoding="utf-8") as f:
    f.write('''"""API Router Aggregator for PeX Platform."""
from fastapi import APIRouter

from app.api.endpoints import (
    auth, cases, events, approvals, actions, analytics,
    adapters, governance, ontology, copilot, audit
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
''')

# 2. main.py
with open(os.path.join(app_dir, "main.py"), "w", encoding="utf-8") as f:
    f.write('''"""PeX Enterprise Platform: FastAPI Application Entrypoint."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.router import api_router
from app.services.data_loader import repo
from app.services.audit_service import audit_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Institutional-grade Payment Exception Resolution Framework for Bank-Agnostic Processing."
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Preload Synthetic Data & Initial Provenance Chain
@app.on_event("startup")
def startup_db_client():
    print("Initializing PeX Database & Preloading Synthetic Data Fixtures...")
    repo.load_all_data()
    
    # Log system genesis audit event if empty
    if not repo.audit_log:
        audit_service.log_event(
            case_id="SYS-INIT",
            correlation_id="CORR-INIT-001",
            stage_name="SYSTEM_INITIALIZATION",
            actor_id="PEX-KERNEL",
            actor_role="SYSTEM",
            action_name="PLATFORM_INITIALIZED",
            details="PeX Enterprise Platform initialized with 18 canonical tables, isolated token vault, and deterministic model gateway.",
            control_tags=["Genesis block created", "Token vault isolated", "RBAC initialized"]
        )
    print("PeX Enterprise Platform Startup Complete!")

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "version": settings.VERSION,
        "mode": settings.MODEL_GATEWAY_MODE,
        "cases_count": len(repo.cases),
        "audit_events_count": len(repo.audit_log),
        "latest_audit_hash": repo.latest_chain_hash
    }

# Mount Frontend Static Build if available
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return None
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
''')

print("Wrote router.py and main.py")

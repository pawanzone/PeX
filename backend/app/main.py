"""PeX Enterprise Platform: FastAPI Application Entrypoint."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.router import api_router
from app.services.data_loader import repo
from app.services.audit_service import audit_service
from app.services.file_watcher import file_watcher


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

from app.db.session import get_db_info

# Startup Event: Preload Synthetic Data & Initial Provenance Chain
@app.on_event("startup")
def startup_db_client():
    print("Initializing PeX Database & Syncing Data Fixtures...")
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
            details="PeX Enterprise Platform initialized with persistent relational database, isolated token vault, and deterministic model gateway.",
            control_tags=["Genesis block created", "Token vault isolated", "RBAC initialized", "DB persistent"]
        )

    # Start Inbound File Watcher if enabled
    if getattr(settings, "WATCHER_ENABLED", True):
        file_watcher.start(initial_scan_baseline=True)
        print(f"[PeX Watcher] Inbound file monitoring active on {file_watcher.input_dir}")

    print("PeX Enterprise Platform Startup Complete!")

@app.on_event("shutdown")
def shutdown_services():
    print("Shutting down PeX services...")
    file_watcher.stop()
    print("PeX Inbound File Monitoring stopped cleanly.")

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    db_info = get_db_info()
    return {
        "status": "HEALTHY",
        "version": settings.VERSION,
        "mode": settings.MODEL_GATEWAY_MODE,
        "database": db_info,
        "cases_count": len(repo.cases),
        "audit_events_count": len(repo.audit_log),
        "latest_audit_hash": repo.latest_chain_hash,
        "file_watcher": file_watcher.get_status()
    }



# Mount Frontend Static Build if available
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail=f"API endpoint '/{full_path}' not found")
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

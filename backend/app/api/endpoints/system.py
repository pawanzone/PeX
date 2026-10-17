"""System info endpoint (mode, simulated-bank flag, LLM status). Filled in by P0.5."""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/info")
def system_info():
    return {
        "version": settings.VERSION,
        "operation_mode": settings.PEX_OPERATION_MODE.upper(),
        "bank_comm": settings.BANK_COMM_MODE,
        "demo": settings.PEX_DEMO,
        "llm": {"enabled": settings.LLM_ENABLED, "model": settings.LLM_MODEL, "reachable": None},
    }

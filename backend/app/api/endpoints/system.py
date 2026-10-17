"""System info endpoint (mode, simulated-bank flag, LLM status). Filled in by P0.5."""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()


def _llm_section():
    # --- llm section (owned by the LLM gateway work) ---
    try:
        from app.services.llm_provider import llm_provider
        return llm_provider.status_summary()
    except Exception:
        return {"enabled": settings.LLM_ENABLED, "model": settings.LLM_MODEL, "reachable": None}

@router.get("/info")
def system_info():
    return {
        "version": settings.VERSION,
        "operation_mode": settings.PEX_OPERATION_MODE.upper(),
        "bank_comm": settings.BANK_COMM_MODE,
        "demo": settings.PEX_DEMO,
        "llm": _llm_section(),
    }

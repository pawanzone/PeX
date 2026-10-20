"""Authentication & Persona Endpoints (demo persona login; production identity = bank IdP/SSO, not built yet)."""
from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional
import hmac

from app.config import settings
from app.core.auth import create_token, resolve_user_id
from app.schemas.auth import UserPersona, LoginRequest, LoginResponse, SigninRequest
from app.core.security import DEMO_PERSONAS, get_persona

router = APIRouter()


def _require_demo():
    if not settings.PEX_DEMO:
        raise HTTPException(status_code=404, detail="Persona login is disabled (PEX_DEMO=false). Configure bank SSO.")


@router.get("/personas", response_model=List[UserPersona])
def list_personas():
    _require_demo()
    return list(DEMO_PERSONAS.values())


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    _require_demo()
    persona = get_persona(req.user_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return LoginResponse(access_token=create_token(persona.user_id), token_type="bearer", user=persona)


@router.post("/signin", response_model=LoginResponse)
def signin(req: SigninRequest):
    """Sign-in screen: user + shared demo password. Same answer for a wrong password and an unknown user."""
    _require_demo()
    persona = get_persona(req.user_id)
    ok = bool(req.password) and hmac.compare_digest(req.password.encode(), settings.PEX_DEMO_PASSWORD.encode())
    if not persona or not ok:
        raise HTTPException(status_code=401, detail="User or password is not correct")
    return LoginResponse(access_token=create_token(persona.user_id), token_type="bearer", user=persona)


@router.get("/me", response_model=UserPersona)
def get_current_user(authorization: Optional[str] = Header(None)):
    user_id = resolve_user_id(authorization, default="OP-8472")
    persona = get_persona(user_id)
    if not persona:
        raise HTTPException(status_code=401, detail="Unknown user")
    return persona

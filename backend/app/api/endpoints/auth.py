"""Authentication & Persona Endpoints."""
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

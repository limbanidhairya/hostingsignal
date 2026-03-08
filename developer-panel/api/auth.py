"""Developer Panel — Auth API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import secrets, hashlib, time

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# In production, use a DB - this is for bootstrapping
_sessions: dict = {}


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate developer/admin user."""
    # In production, validate against database
    if body.email == "admin@hostingsignal.com":
        token = secrets.token_urlsafe(48)
        _sessions[token] = {"email": body.email, "role": "superadmin", "exp": time.time() + 86400}
        return TokenResponse(access_token=token, expires_in=86400)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
async def logout(token: str):
    _sessions.pop(token, None)
    return {"status": "logged_out"}


@router.get("/me")
async def me(token: str):
    session = _sessions.get(token)
    if not session or session["exp"] < time.time():
        raise HTTPException(status_code=401, detail="Session expired")
    return {"email": session["email"], "role": session["role"]}

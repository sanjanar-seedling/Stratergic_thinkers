"""Auth Routes — Signup, Login, and user info endpoints."""

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory user store (replace with DB queries in production) ──
_users: list[dict] = []


# ── Schemas ──


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str


# ── Routes ──


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest):
    """Register a new user and return JWT."""
    # Check if email already exists
    existing = next((u for u in _users if u["email"] == data.email), None)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate password
    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters",
        )

    user = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "display_name": data.display_name or data.email.split("@")[0],
        "password_hash": hash_password(data.password),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    _users.append(user)

    token = create_access_token(user["id"], user["email"])
    logger.info(f"New user registered: {user['email']}")

    return AuthResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Authenticate user and return JWT."""
    user = next((u for u in _users if u["email"] == data.email), None)

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = create_access_token(user["id"], user["email"])
    logger.info(f"User logged in: {user['email']}")

    return AuthResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
        },
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    # Find user in store to get full profile
    user = next((u for u in _users if u["id"] == current_user["id"]), None)

    if user:
        return {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "created_at": user["created_at"],
        }

    # If user not found in memory (e.g. server restarted), return token data
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "display_name": current_user["email"].split("@")[0],
        "created_at": datetime.utcnow().isoformat(),
    }

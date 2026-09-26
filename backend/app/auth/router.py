"""
Authentication Router
Endpoints for user login, registration, and profile retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.app.auth.jwt_handler import create_access_token
from backend.app.auth.user_service import authenticate_user, create_user, get_user_by_email
from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field("citizen", description="Role: forecaster, admin, or citizen")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    user_id: int


class UserProfileResponse(BaseModel):
    user_id: int
    email: str
    role: str


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db=Depends(get_db)):
    """
    Authenticate user with email and password; issues JWT with embedded role.
    """
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "email": user["email"],
        "user_id": user["user_id"],
    }


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db=Depends(get_db)):
    """
    Register a new user account with bcrypt-hashed password; issues initial JWT.
    """
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    if payload.role not in {"forecaster", "admin", "citizen"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'forecaster', 'admin', or 'citizen'.",
        )

    user = create_user(db, payload.email, payload.password, payload.role)
    token = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "email": user["email"],
        "user_id": user["user_id"],
    }


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(user=Depends(get_current_user)):
    """
    Returns the authenticated user's profile and assigned role.
    """
    return user

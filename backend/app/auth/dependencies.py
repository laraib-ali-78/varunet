"""
FastAPI Dependencies for Role-Based Access Control and Rate Limiting
"""

import time
from typing import List, Dict, Any, Callable
from collections import defaultdict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from backend.app.auth.jwt_handler import decode_access_token

security = HTTPBearer(auto_error=False)

# 4. Basic In-Memory Rate Limiter for Citizen-Accessible Public Routes
# Tracks request timestamps per client IP (window: 60 seconds, limit: 60 requests)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60
_CLIENT_REQUEST_LOG: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(request: Request):
    """
    Enforces basic sliding-window rate limiting on public routes.
    Returns HTTP 429 when client IP exceeds 60 requests per minute.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    timestamps = _CLIENT_REQUEST_LOG[client_ip]

    # Purge requests older than window
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    _CLIENT_REQUEST_LOG[client_ip] = [t for t in timestamps if t > cutoff]

    if len(_CLIENT_REQUEST_LOG[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 60 requests per minute allowed.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    _CLIENT_REQUEST_LOG[client_ip].append(now)


def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Validates the Bearer JWT token from the Authorization header.
    Returns decoded user payload (sub, email, role).
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Expected 'Bearer <JWT>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(auth.credentials)
        return {
            "user_id": int(payload["sub"]),
            "email": payload["email"],
            "role": payload["role"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    3. Factory function returning a FastAPI dependency that enforces role-based
       access control per route.
       forecaster / admin / citizen
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{user_role}' does not have permission for this resource. Required one of: {allowed_roles}",
            )
        return user

    return role_checker

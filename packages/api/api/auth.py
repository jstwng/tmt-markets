"""FastAPI dependency for JWT-based authentication via Supabase."""

import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

_bearer_scheme = HTTPBearer()

_jwt_secret: str | None = None


def _get_jwt_secret() -> str:
    global _jwt_secret
    if _jwt_secret is None:
        _jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
        if not _jwt_secret:
            raise RuntimeError("SUPABASE_JWT_SECRET is not set")
    return _jwt_secret


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """Verify Supabase JWT and return the authenticated user."""
    token = credentials.credentials

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    expected_issuer = f"{supabase_url}/auth/v1" if supabase_url else None

    decode_kwargs: dict = {
        "algorithms": ["HS256"],
        "audience": "authenticated",
        "leeway": 30,
    }
    if expected_issuer:
        decode_kwargs["issuer"] = expected_issuer

    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            **decode_kwargs,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub claim")

    return AuthenticatedUser(id=user_id, email=email)

"""FastAPI dependency for JWT-based authentication via Supabase."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError
from pydantic import BaseModel

from api.supabase_client import get_service_client

_bearer_scheme = HTTPBearer()


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """Verify Supabase JWT via the admin API and return the authenticated user.

    Delegates all algorithm/signature checking to the Supabase SDK so we
    don't need to hard-code HS256/RS256 or manage keys manually.
    """
    token = credentials.credentials
    try:
        response = get_service_client().auth.get_user(token)
        user = response.user
    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth error: {e}",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
        )

    return AuthenticatedUser(id=user.id, email=user.email)

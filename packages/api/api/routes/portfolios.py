"""REST endpoints for portfolio CRUD."""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import get_current_user, AuthenticatedUser
from api.supabase_client import get_user_client

router = APIRouter(tags=["portfolios"])
_bearer_scheme = HTTPBearer()


@router.get("/portfolios")
async def list_portfolios(
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = sb.table("portfolios") \
        .select("id, name, tickers, weights, constraints, metadata, created_at, updated_at") \
        .eq("user_id", user.id) \
        .order("updated_at", desc=True) \
        .execute()
    return result.data


@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    sb.table("portfolios").delete().eq("id", portfolio_id).execute()
    return {"deleted": portfolio_id}

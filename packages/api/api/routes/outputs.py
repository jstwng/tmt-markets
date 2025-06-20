"""REST endpoints for saved outputs."""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import get_current_user, AuthenticatedUser
from api.supabase_client import get_user_client

router = APIRouter(tags=["outputs"])
_bearer_scheme = HTTPBearer()


@router.get("/outputs")
async def list_outputs(
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = sb.table("saved_outputs") \
        .select("id, label, output_type, conversation_id, created_at") \
        .eq("user_id", user.id) \
        .order("created_at", desc=True) \
        .execute()
    return result.data


@router.delete("/outputs/{output_id}")
async def delete_output(
    output_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    sb.table("saved_outputs").delete().eq("id", output_id).execute()
    return {"deleted": output_id}

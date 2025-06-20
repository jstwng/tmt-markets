"""Supabase client helpers — service-role singleton and per-request user-scoped client."""

import os

from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions

_service_client: Client | None = None


def _get_env(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        raise RuntimeError(f"{key} is not set")
    return value


def get_service_client() -> Client:
    """Return a Supabase client using the service-role key (bypasses RLS)."""
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            _get_env("SUPABASE_URL"),
            _get_env("SUPABASE_SERVICE_ROLE_KEY"),
        )
    return _service_client


def get_user_client(access_token: str) -> Client:
    """Return a Supabase client scoped to a user's JWT (respects RLS).

    Passes the JWT as an Authorization header at client construction time —
    no extra network call is made. Creates a fresh client per request.
    """
    opts = SyncClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
        auto_refresh_token=False,
        persist_session=False,
    )
    return create_client(
        _get_env("SUPABASE_URL"),
        _get_env("SUPABASE_ANON_KEY"),
        options=opts,
    )

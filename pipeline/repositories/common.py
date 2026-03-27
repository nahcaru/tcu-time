from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from supabase import Client, create_client

from pipeline.core.settings import Settings

Row = dict[str, Any]

_client: Client | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_client() -> Client:
    global _client
    if _client is None:
        Settings.validate(required=("SUPABASE_URL", "SUPABASE_KEY"))
        _client = create_client(Settings.SUPABASE_URL, Settings.SUPABASE_KEY)
    return _client


def first_row(data: Any) -> Row:
    return cast(Row, data[0])

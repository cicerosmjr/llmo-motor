"""Cliente HTTP mínimo para PostgREST do Supabase (service role)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def supabase_configurado() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


class SupabaseRest:
    """Wrapper sync sobre /rest/v1 — adequado ao JobStore/Banco (métodos síncronos)."""

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.base or not self.key:
            raise RuntimeError(
                "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios"
            )
        self._headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._client = httpx.Client(
            base_url=f"{self.base}/rest/v1",
            headers=self._headers,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def select(
        self,
        table: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        r = self._client.get(f"/{table}", params=params or {}, headers=headers or {})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]] | dict[str, Any],
        *,
        on_conflict: str = "id",
    ) -> list[dict[str, Any]]:
        payload = rows if isinstance(rows, list) else [rows]
        r = self._client.post(
            f"/{table}",
            json=payload,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": on_conflict},
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def delete(self, table: str, *, params: dict[str, str]) -> None:
        r = self._client.delete(f"/{table}", params=params)
        r.raise_for_status()

    def ok(self) -> bool:
        try:
            # HEAD leve — só valida rede + auth + tabela
            r = self._client.get(
                "/llmo_jobs",
                params={"select": "job_id", "limit": "1"},
            )
            return r.status_code < 400
        except Exception as e:  # noqa: BLE001
            logger.warning("Supabase health falhou: %s", e)
            return False

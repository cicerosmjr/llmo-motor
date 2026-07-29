"""Persistência de jobs — disco local (Railway) ou Supabase (Vercel)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from services.supabase_rest import SupabaseRest, supabase_configurado

logger = logging.getLogger(__name__)


class JobStore:
    """API única: salvar / get / delete / listar / ok.

    - Sem SUPABASE_* → JSON em pasta (comportamento original).
    - Com SUPABASE_* → tabela llmo_jobs (necessário na Vercel).
    """

    def __init__(
        self,
        pasta: str | Path = "data/jobs",
        *,
        supabase: SupabaseRest | None = None,
        usar_supabase: bool | None = None,
    ) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._sb: SupabaseRest | None = None
        self.pasta: Path | None = None

        if usar_supabase is None:
            usar_supabase = supabase is not None or supabase_configurado()

        if usar_supabase:
            self._sb = supabase or SupabaseRest()
            logger.info("JobStore: backend Supabase")
            self.carregar(dias=90)
        else:
            self.pasta = Path(pasta)
            try:
                self.pasta.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(
                    "JobStore: não foi possível criar %s (%s). "
                    "Em filesystem read-only (Vercel), configure SUPABASE_URL "
                    "e SUPABASE_SERVICE_ROLE_KEY.",
                    self.pasta,
                    e,
                )
                raise
            logger.info("JobStore: backend disco em %s", self.pasta)
            self.carregar(dias=90)

    def _path(self, job_id: UUID | str) -> Path:
        assert self.pasta is not None
        return self.pasta / f"{job_id}.json"

    def carregar(self, dias: int = 90) -> None:
        if self._sb is not None:
            self._carregar_supabase(dias)
            return
        assert self.pasta is not None
        limite = datetime.utcnow() - timedelta(days=dias)
        for arquivo in self.pasta.glob("*.json"):
            try:
                raw = json.loads(arquivo.read_text(encoding="utf-8"))
                updated = raw.get("updated_at")
                if updated:
                    dt = datetime.fromisoformat(updated.replace("Z", ""))
                    if dt < limite:
                        continue
                self._cache[str(raw.get("job_id", arquivo.stem))] = raw
            except Exception as e:  # noqa: BLE001
                logger.warning("Falha ao carregar job %s: %s", arquivo, e)
        logger.info("JobStore: %s jobs em cache", len(self._cache))

    def _carregar_supabase(self, dias: int) -> None:
        assert self._sb is not None
        limite = (datetime.utcnow() - timedelta(days=dias)).isoformat()
        try:
            rows = self._sb.select(
                "llmo_jobs",
                params={
                    "select": "job_id,payload,updated_at",
                    "updated_at": f"gte.{limite}",
                    "order": "updated_at.desc",
                },
            )
            for row in rows:
                payload = dict(row.get("payload") or {})
                key = str(row.get("job_id") or payload.get("job_id"))
                payload["job_id"] = key
                if row.get("updated_at"):
                    payload.setdefault("updated_at", row["updated_at"])
                self._cache[key] = payload
            logger.info("JobStore: %s jobs carregados do Supabase", len(self._cache))
        except Exception as e:  # noqa: BLE001
            logger.error("JobStore: falha ao carregar do Supabase: %s", e)
            raise

    def salvar(self, job_id: UUID | str, dados: dict[str, Any]) -> None:
        key = str(job_id)
        payload = dict(dados)
        payload["job_id"] = key
        payload["updated_at"] = datetime.utcnow().isoformat()
        self._cache[key] = payload

        if self._sb is not None:
            self._sb.upsert(
                "llmo_jobs",
                {
                    "job_id": key,
                    "payload": payload,
                    "updated_at": payload["updated_at"],
                },
                on_conflict="job_id",
            )
            return

        assert self.pasta is not None
        self._path(key).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def get(self, job_id: UUID | str) -> dict[str, Any] | None:
        key = str(job_id)
        # No Supabase, polling de status chega em outra invocação serverless:
        # sempre reidrata do banco (cache local só acelera o mesmo processo).
        if self._sb is not None:
            try:
                rows = self._sb.select(
                    "llmo_jobs",
                    params={
                        "select": "job_id,payload,updated_at",
                        "job_id": f"eq.{key}",
                        "limit": "1",
                    },
                )
                if not rows:
                    return None
                payload = dict(rows[0].get("payload") or {})
                payload["job_id"] = key
                if rows[0].get("updated_at"):
                    payload.setdefault("updated_at", rows[0]["updated_at"])
                self._cache[key] = payload
                return payload
            except Exception as e:  # noqa: BLE001
                logger.warning("JobStore.get Supabase falhou, usando cache: %s", e)
                return self._cache.get(key)
        return self._cache.get(key)

    def delete(self, job_id: UUID | str) -> bool:
        key = str(job_id)
        existed = key in self._cache
        if self._sb is not None:
            # Confirma existência no banco (cache pode estar vazio em cold start)
            atual = self.get(job_id)
            if not atual:
                return False
            self._cache.pop(key, None)
            self._sb.delete("llmo_jobs", params={"job_id": f"eq.{key}"})
            return True

        if not existed:
            return False
        del self._cache[key]
        assert self.pasta is not None
        path = self._path(key)
        if path.exists():
            path.unlink()
        return True

    def listar(self) -> list[dict[str, Any]]:
        if self._sb is not None:
            # Lista fresca para histórico em ambiente multi-instância
            try:
                self._cache.clear()
                self._carregar_supabase(dias=90)
            except Exception as e:  # noqa: BLE001
                logger.warning("JobStore.listar: usando cache local: %s", e)
        return list(self._cache.values())

    def ok(self) -> bool:
        if self._sb is not None:
            return self._sb.ok()
        assert self.pasta is not None
        try:
            teste = self.pasta / ".write_test"
            teste.write_text("ok", encoding="utf-8")
            teste.unlink(missing_ok=True)
            return True
        except Exception:  # noqa: BLE001
            return False

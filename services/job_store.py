"""Persistência de jobs em data/jobs/*.json + cache em memória."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class JobStore:
    def __init__(self, pasta: str | Path = "data/jobs") -> None:
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = {}
        self.carregar(dias=90)

    def _path(self, job_id: UUID | str) -> Path:
        return self.pasta / f"{job_id}.json"

    def carregar(self, dias: int = 90) -> None:
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

    def salvar(self, job_id: UUID | str, dados: dict[str, Any]) -> None:
        key = str(job_id)
        payload = dict(dados)
        payload["job_id"] = key
        payload["updated_at"] = datetime.utcnow().isoformat()
        self._cache[key] = payload
        self._path(key).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def get(self, job_id: UUID | str) -> dict[str, Any] | None:
        return self._cache.get(str(job_id))

    def delete(self, job_id: UUID | str) -> bool:
        key = str(job_id)
        if key not in self._cache:
            return False
        del self._cache[key]
        path = self._path(key)
        if path.exists():
            path.unlink()
        return True

    def listar(self) -> list[dict[str, Any]]:
        return list(self._cache.values())

    def ok(self) -> bool:
        try:
            teste = self.pasta / ".write_test"
            teste.write_text("ok", encoding="utf-8")
            teste.unlink(missing_ok=True)
            return True
        except Exception:  # noqa: BLE001
            return False

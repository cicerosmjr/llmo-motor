"""Serviço OpenAI (ChatGPT) para consultas LLMO — gpt-4o + busca web."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from openai import AsyncOpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIService:
    """Chamadas orgânicas: só a pergunta, sem contexto de empresa nem system Vertice."""

    MODELO = "gpt-4o"
    MAX_TOKENS = 1500
    # Preços por 1K tokens (gpt-4o: $2.50 / $10.00 por 1M)
    PRECO_INPUT = 0.0025
    PRECO_OUTPUT = 0.01
    # Web search: $10 / 1k calls → $0.01 por chamada
    PRECO_WEB_SEARCH = 0.01
    USD_BRL = 5.5
    TIMEOUT_SEG = 90.0

    def __init__(self, api_key: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.api_key = api_key

    async def consultar(
        self, pergunta: str, contexto: str = "", *, usar_busca: bool = True
    ) -> str:
        """contexto é ignorado — mantido só por compatibilidade de assinatura."""
        _ = contexto
        if not self.client:
            return "ERRO_API: OPENAI_API_KEY ausente"

        delays = [1, 2, 4]
        ultimo_erro = ""
        kwargs: dict = {
            "model": self.MODELO,
            "max_output_tokens": self.MAX_TOKENS,
            "input": pergunta,
        }
        if usar_busca:
            kwargs["tools"] = [{"type": "web_search"}]
            kwargs["tool_choice"] = "required"

        for delay in delays + [None]:
            try:
                resp = await asyncio.wait_for(
                    self.client.responses.create(**kwargs),
                    timeout=self.TIMEOUT_SEG if usar_busca else 30.0,
                )
                texto = (getattr(resp, "output_text", None) or "").strip()
                if not texto:
                    texto = self._extrair_texto(resp)
                uso = getattr(resp, "usage", None)
                tokens = 0
                custo = self.PRECO_WEB_SEARCH if usar_busca else 0.0
                if uso:
                    in_t = getattr(uso, "input_tokens", None) or getattr(
                        uso, "prompt_tokens", 0
                    ) or 0
                    out_t = getattr(uso, "output_tokens", None) or getattr(
                        uso, "completion_tokens", 0
                    ) or 0
                    tokens = in_t + out_t
                    custo += (in_t / 1000) * self.PRECO_INPUT + (
                        out_t / 1000
                    ) * self.PRECO_OUTPUT
                logger.info(
                    "[ChatGPT] '%s...' | tokens=%s | custo=$%.4f | busca=%s",
                    pergunta[:50],
                    tokens,
                    custo,
                    usar_busca,
                )
                return texto or ""
            except RateLimitError as e:
                ultimo_erro = str(e)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            except APIError as e:
                logger.error("[ChatGPT] APIError: %s", e)
                return f"ERRO_API: {e}"
            except asyncio.TimeoutError:
                return "ERRO_TIMEOUT"
            except Exception as e:  # noqa: BLE001
                logger.error("[ChatGPT] erro: %s", e)
                return f"ERRO_API: {e}"

        return f"ERRO_API: RateLimit — {ultimo_erro}"

    @staticmethod
    def _extrair_texto(resp: object) -> str:
        partes: list[str] = []
        for item in getattr(resp, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for block in getattr(item, "content", None) or []:
                text = getattr(block, "text", None)
                if text:
                    partes.append(text)
        return "\n".join(partes).strip()

    async def consultar_lote(
        self,
        perguntas: list[tuple[UUID, str]],
        contexto: str = "",
        delay: float = 0.5,
    ) -> list[tuple[UUID, str]]:
        _ = contexto
        resultados: list[tuple[UUID, str]] = []
        for i, (pid, texto) in enumerate(perguntas):
            resposta = await self.consultar(texto)
            resultados.append((pid, resposta))
            if i < len(perguntas) - 1:
                await asyncio.sleep(delay)
        return resultados

    def estimar_custo(self, num_perguntas: int) -> dict:
        input_t = num_perguntas * 200
        output_t = num_perguntas * 800
        usd = (
            (input_t / 1000) * self.PRECO_INPUT
            + (output_t / 1000) * self.PRECO_OUTPUT
            + num_perguntas * self.PRECO_WEB_SEARCH
        )
        return {
            "usd": round(usd, 4),
            "brl": round(usd * self.USD_BRL, 2),
            "tokens_estimados": input_t + output_t,
        }

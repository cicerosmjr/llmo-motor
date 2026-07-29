"""Serviço Perplexity (busca em tempo real) para consultas LLMO."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from openai import AsyncOpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)


class PerplexityService:
    """Modelo sonar (mesmo do site) — busca nativa; pergunta orgânica sem contexto."""

    MODELO = "sonar"
    MAX_TOKENS = 1500
    TEMPERATURE = 0.3
    BASE_URL = "https://api.perplexity.ai"
    PRECO_INPUT = 0.001
    PRECO_OUTPUT = 0.001
    USD_BRL = 5.5

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = (
            AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL) if api_key else None
        )

    async def consultar(self, pergunta: str, contexto: str = "") -> str:
        """contexto é ignorado — medição orgânica sem dica da empresa."""
        _ = contexto
        if not self.client:
            return "ERRO_API: PERPLEXITY_API_KEY ausente"

        delays = [1, 2, 4]
        ultimo_erro = ""

        for delay in delays + [None]:
            try:
                resp = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.MODELO,
                        max_tokens=self.MAX_TOKENS,
                        temperature=self.TEMPERATURE,
                        messages=[
                            {"role": "user", "content": pergunta},
                        ],
                    ),
                    timeout=60,
                )
                texto = resp.choices[0].message.content or ""
                uso = resp.usage
                tokens = uso.total_tokens if uso else 0
                custo = 0.0
                if uso:
                    custo = (
                        (uso.prompt_tokens / 1000) * self.PRECO_INPUT
                        + (uso.completion_tokens / 1000) * self.PRECO_OUTPUT
                    )
                logger.info(
                    "[Perplexity REAL-TIME] '%s...' | tokens=%s | custo=$%.4f",
                    pergunta[:50],
                    tokens,
                    custo,
                )
                return texto
            except RateLimitError as e:
                ultimo_erro = str(e)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            except APIError as e:
                logger.error("[Perplexity] APIError: %s", e)
                return f"ERRO_API: {e}"
            except asyncio.TimeoutError:
                return "ERRO_TIMEOUT"
            except Exception as e:  # noqa: BLE001
                logger.error("[Perplexity] erro: %s", e)
                return f"ERRO_API: {e}"

        return f"ERRO_API: RateLimit — {ultimo_erro}"

    async def consultar_lote(
        self,
        perguntas: list[tuple[UUID, str]],
        contexto: str = "",
        delay: float = 1.0,
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
        output_t = num_perguntas * 400
        usd = (input_t / 1000) * self.PRECO_INPUT + (output_t / 1000) * self.PRECO_OUTPUT
        return {
            "usd": round(usd, 4),
            "brl": round(usd * self.USD_BRL, 2),
            "tokens_estimados": input_t + output_t,
        }

"""Serviço Gemini para consultas LLMO."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from services.claude_service import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GeminiService:
    MODELO = "gemini-3.6-flash"
    MAX_TOKENS = 1500
    TEMPERATURE = 0.3
    SYSTEM_PROMPT = SYSTEM_PROMPT
    PRECO_INPUT = 0.000075
    PRECO_OUTPUT = 0.0003
    USD_BRL = 5.5

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._model = None
        if api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(
                    self.MODELO,
                    system_instruction=self.SYSTEM_PROMPT,
                )
            except Exception as e:  # noqa: BLE001
                logger.error("[Gemini] falha ao inicializar: %s", e)

    def _consultar_sync(self, pergunta: str) -> str:
        if not self._model:
            return "ERRO_API: GOOGLE_API_KEY ausente"
        try:
            import google.generativeai as genai

            resp = self._model.generate_content(
                pergunta,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                ),
            )
            texto = resp.text or ""
            logger.info("[Gemini] '%s...' | len=%s", pergunta[:50], len(texto))
            return texto
        except Exception as e:  # noqa: BLE001
            logger.error("[Gemini] erro: %s", e)
            msg = str(e).lower()
            if "timeout" in msg:
                return "ERRO_TIMEOUT"
            return f"ERRO_API: {e}"

    async def consultar(self, pergunta: str, contexto: str = "") -> str:
        """contexto é ignorado — medição orgânica sem dica da empresa."""
        _ = contexto
        delays = [1, 2, 4]
        ultimo = ""
        for delay in delays + [None]:
            try:
                resultado = await asyncio.wait_for(
                    asyncio.to_thread(self._consultar_sync, pergunta),
                    timeout=30,
                )
                if resultado.startswith("ERRO_API:") and "429" in resultado and delay:
                    await asyncio.sleep(delay)
                    ultimo = resultado
                    continue
                return resultado
            except asyncio.TimeoutError:
                return "ERRO_TIMEOUT"
            except Exception as e:  # noqa: BLE001
                ultimo = str(e)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
        return f"ERRO_API: {ultimo}"

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
        output_t = num_perguntas * 400
        usd = (input_t / 1000) * self.PRECO_INPUT + (output_t / 1000) * self.PRECO_OUTPUT
        return {
            "usd": round(usd, 4),
            "brl": round(usd * self.USD_BRL, 2),
            "tokens_estimados": input_t + output_t,
        }

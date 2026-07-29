"""Serviço Claude (Anthropic) para consultas LLMO."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Você é um assistente útil respondendo perguntas de "
    "usuários brasileiros que buscam empresas e serviços profissionais nas "
    "áreas de saúde, direito e psicologia. Responda de forma natural e "
    "honesta com base no que você conhece. Se não souber ou não tiver certeza "
    "sobre uma empresa específica, diga isso claramente em vez de inventar."
)


class ClaudeService:
    """Cliente Claude com chamadas JSON isoladas (sem sessão/histórico).

    Sem contexto de empresa e sem busca web: o Claude tende a ser conservador
    e pode não citar nenhuma clínica. `nao_citado` é resultado LLMO válido —
    mede visibilidade real, não falha técnica.
    """

    # ISOLAMENTO DE CONTEXTO
    # Cada chamada à API é completamente stateless.
    # Nunca acumular histórico de mensagens entre chamadas.
    # Objetivo: medir o que a IA sabe sobre a empresa de forma neutra,
    # sem ancoragem de perguntas anteriores ou diagnósticos anteriores.

    MODELO = "claude-sonnet-5"
    MAX_TOKENS = 600
    # Sonnet 5: não enviar temperature custom

    SYSTEM_PROMPT = SYSTEM_PROMPT

    # Estimativa USD por 1K tokens
    PRECO_INPUT = 0.003
    PRECO_OUTPUT = 0.015
    USD_BRL = 5.5

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None
        self.api_key = api_key

    async def consultar(self, pergunta: str, contexto: str = "") -> str:
        assert isinstance(pergunta, str) and len(pergunta) > 0
        # Garante que nenhum objeto de histórico foi passado por engano

        if not self.client:
            return "ERRO_API: ANTHROPIC_API_KEY ausente"

        # messages: APENAS a pergunta atual — sem histórico e sem contexto de empresa.
        # `contexto` é ignorado de propósito (assinatura mantida para interface comum).
        _ = contexto
        delays = [1, 2, 4]
        ultimo_erro = ""

        for tentativa, delay in enumerate(delays + [None]):
            try:
                resp = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.MODELO,
                        max_tokens=self.MAX_TOKENS,
                        system=self.SYSTEM_PROMPT,
                        messages=[
                            {"role": "user", "content": pergunta},
                        ],
                    ),
                    timeout=30,
                )
                texto = "".join(
                    block.text for block in resp.content if hasattr(block, "text")
                )
                uso = getattr(resp, "usage", None)
                tokens = (uso.input_tokens + uso.output_tokens) if uso else 0
                custo = (
                    (uso.input_tokens / 1000) * self.PRECO_INPUT
                    + (uso.output_tokens / 1000) * self.PRECO_OUTPUT
                ) if uso else 0.0
                logger.info(
                    "[Claude] '%s...' | tokens=%s | custo=$%.4f",
                    pergunta[:50],
                    tokens,
                    custo,
                )
                return texto
            except anthropic.RateLimitError as e:
                ultimo_erro = str(e)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            except anthropic.APIError as e:
                logger.error("[Claude] APIError: %s", e)
                return f"ERRO_API: {e}"
            except asyncio.TimeoutError:
                return "ERRO_TIMEOUT"
            except Exception as e:  # noqa: BLE001
                logger.error("[Claude] erro: %s", e)
                return f"ERRO_API: {e}"

        return f"ERRO_API: RateLimit — {ultimo_erro}"

    async def consultar_lote(
        self,
        perguntas: list[tuple[UUID, str]],
        contexto: str = "",
        delay: float = 0.5,
    ) -> list[tuple[UUID, str]]:
        # Cada iteração chama consultar() de forma isolada —
        # resultados anteriores NUNCA entram no messages da próxima pergunta.
        _ = contexto
        resultados: list[tuple[UUID, str]] = []
        for i, (pid, texto) in enumerate(perguntas):
            resposta = await self.consultar(texto)
            resultados.append((pid, resposta))
            if i < len(perguntas) - 1:
                await asyncio.sleep(delay)
        return resultados

    def estimar_custo(self, num_perguntas: int) -> dict:
        tokens = num_perguntas * 600
        usd = (tokens / 1000) * (self.PRECO_INPUT + self.PRECO_OUTPUT) / 2 * 2
        # aproximação: metade input / metade output no volume estimado
        input_t = num_perguntas * 200
        output_t = num_perguntas * 400
        usd = (input_t / 1000) * self.PRECO_INPUT + (output_t / 1000) * self.PRECO_OUTPUT
        return {
            "usd": round(usd, 4),
            "brl": round(usd * self.USD_BRL, 2),
            "tokens_estimados": input_t + output_t,
        }

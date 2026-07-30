"""Orquestrador do diagnóstico LLMO."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Callable
from typing import Any
from uuid import UUID

from models.schemas import (
    DiagnosticoRequest,
    DiagnosticoResult,
    NivelCitacaoEnum,
    ResultadoIA,
    ScoreDimensao,
)
from prompts.banco import BancoPerguntas
from prompts.substituidor import preparar_perguntas_diagnostico
from scoring.engine import ScoringEngine
from services.site_auditor import SiteAuditor

logger = logging.getLogger(__name__)


class LLMOOrchestrator:
    def __init__(
        self,
        claude: Any,
        openai: Any,
        gemini: Any,
        perplexity: Any,
        banco: BancoPerguntas,
        auditor: SiteAuditor | None = None,
    ) -> None:
        self.servicos = {
            "claude": claude,
            "chatgpt": openai,
            "gemini": gemini,
            "perplexity": perplexity,
        }
        self.banco = banco
        self.auditor = auditor or SiteAuditor()
        self.scoring = ScoringEngine()

    async def rodar_diagnostico(
        self,
        request: DiagnosticoRequest,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> DiagnosticoResult:
        def progress(etapa: str, pct: int) -> None:
            if progress_callback:
                progress_callback({"etapa": etapa, "pct": pct})

        # 1. Buscar perguntas
        perguntas = []
        for pid in request.perguntas_ids:
            p = self.banco.buscar_por_id(pid)
            if p is None:
                raise ValueError(f"Pergunta {pid} não existe no banco")
            perguntas.append(p)

        mapa_rodada = {
            p.id: p.rodada.value
            for p in perguntas
            if p.rodada is not None
        }

        # 2. Placeholders
        perguntas_prep = preparar_perguntas_diagnostico(perguntas, request)
        mapa_texto = {pid: txt for pid, txt in perguntas_prep}

        # 3. Perguntas orgânicas — sem injetar nome da empresa como "Contexto:"
        # A marca só aparece se estiver no texto da pergunta (ex.: R4 com {empresa}).

        # 4. Auditoria do site (paralela com IAs)
        progress("Auditoria do site", 10)
        servicos_ativos = {
            nome: svc
            for nome, svc in self.servicos.items()
            if nome in request.ias_ativas and svc is not None
        }

        async def _auditar() -> dict:
            return await self.auditor.auditar(request.site_url)

        async def _lote(nome: str, svc: Any) -> tuple[str, list[tuple[UUID, str]]]:
            delay = 1.0 if nome == "perplexity" else 0.5
            res = await svc.consultar_lote(perguntas_prep, delay=delay)
            return nome, res

        auditor_task = asyncio.create_task(_auditar())
        ia_tasks = [
            asyncio.create_task(_lote(nome, svc))
            for nome, svc in servicos_ativos.items()
        ]

        resultados_brutos: list[tuple[str, list[tuple[UUID, str]]]] = []
        total_ias = len(ia_tasks)
        concluidas = 0

        for coro in asyncio.as_completed(ia_tasks):
            nome, res = await coro
            resultados_brutos.append((nome, res))
            concluidas += 1
            pct = 20 + int(60 * concluidas / max(total_ias, 1))
            progress(f"{nome} concluído ({len(res)}/{len(perguntas_prep)})", pct)

        checks = await auditor_task
        progress("Auditoria concluída", 85)

        # 5–6. Avaliar respostas (com teto por rodada R1–R5)
        resultados_ias: list[ResultadoIA] = []
        for ia_nome, pares in resultados_brutos:
            for pid, resposta in pares:
                avaliacao = self.scoring.avaliar_resposta(
                    resposta,
                    request.empresa_nome,
                    rodada=mapa_rodada.get(pid),
                )
                resultados_ias.append(
                    ResultadoIA(
                        ia_nome=ia_nome,
                        pergunta_id=pid,
                        pergunta_texto=mapa_texto.get(pid, ""),
                        resposta_completa=resposta,
                        citou_empresa=avaliacao["citou"],
                        nivel_citacao=NivelCitacaoEnum(avaliacao["nivel"]),
                        pontuacao=avaliacao["pontuacao"],
                        trecho_relevante=avaliacao.get("trecho"),
                        concorrentes_citados=avaliacao.get("concorrentes") or [],
                    )
                )

        # 8. Scores
        seo = self.scoring.calcular_score_seo(checks.get("seo", {}))
        llmo = self.scoring.calcular_score_llmo(checks.get("llmo", {}), resultados_ias)
        autoridade = self.scoring.calcular_score_autoridade(resultados_ias)
        conteudo = self.scoring.calcular_score_conteudo(checks.get("conteudo", {}))
        score_geral, status = self.scoring.calcular_score_geral(
            seo, llmo, autoridade, conteudo
        )
        scores: dict[str, ScoreDimensao] = {
            "seo_tecnico": seo,
            "llmo_schema": llmo,
            "autoridade_citacao": autoridade,
            "conteudo": conteudo,
        }
        # Anexa meta do auditor
        seo.detalhes["meta"] = checks.get("meta", {})

        # 9. Concorrentes
        concorrentes = self._extrair_concorrentes(resultados_ias, request.empresa_nome)

        # 9b. Bloco 1 — Visibilidade nas IAs (métrica paralela; não altera score_geral)
        bloco1 = self.scoring.calcular_bloco1_visibilidade(
            resultados_ias,
            mapa_rodada,
            ias_ativas=request.ias_ativas,
        )

        # 9c. Estrutura da planilha (blocos 2–6 vazios; usuário preenche depois)
        planilha = self.scoring.calcular_blocos_manuais_e_total(
            bloco1_media=bloco1.media,
            notas={},
            segmento=request.segmento.value,
        )

        # 10. Plano de ação
        plano = self._gerar_plano_acao(scores, resultados_ias, request)

        resumo = self.scoring.gerar_resumo_executivo(
            request, score_geral, status, scores, concorrentes
        )

        progress("Diagnóstico concluído", 100)

        return DiagnosticoResult(
            request=request,
            resultados_ias=resultados_ias,
            scores=scores,
            score_geral=score_geral,
            status=status,
            concorrentes_mais_citados=concorrentes,
            plano_acao=plano,
            resumo_executivo=resumo,
            bloco1_visibilidade=bloco1,
            diagnostico_planilha=planilha,
        )

    def _extrair_concorrentes(
        self, resultados: list[ResultadoIA], empresa_nome: str
    ) -> list[dict]:
        contagem: Counter[str] = Counter()
        empresa_l = empresa_nome.lower()
        for r in resultados:
            for nome in r.concorrentes_citados:
                if empresa_l in nome.lower():
                    continue
                contagem[nome] += 1
        return [
            {"nome": n, "vezes_citado": c}
            for n, c in contagem.most_common()
        ]

    def _gerar_plano_acao(
        self,
        scores: dict[str, ScoreDimensao],
        resultados: list[ResultadoIA],
        request: DiagnosticoRequest,
    ) -> list[dict]:
        acoes: list[dict] = []
        seo = scores["seo_tecnico"].pontuacao_bruta
        llmo = scores["llmo_schema"].pontuacao_bruta
        autoridade = scores["autoridade_citacao"].pontuacao_bruta
        conteudo = scores["conteudo"].pontuacao_bruta

        if llmo < 3:
            acoes.append({
                "prioridade": "urgente",
                "acao": f"Implementar Schema JSON-LD LocalBusiness no site de {request.empresa_nome}",
            })
            acoes.append({
                "prioridade": "urgente",
                "acao": "Criar arquivo llms.txt na raiz do domínio",
            })

        if autoridade == 0:
            acoes.append({
                "prioridade": "urgente",
                "acao": "Criar FAQ estruturado com FAQPage Schema (mínimo 8 perguntas)",
            })
            acoes.append({
                "prioridade": "urgente",
                "acao": "Registrar e otimizar perfil no Google Meu Negócio",
            })

        perplexity_citou = any(
            r.ia_nome == "perplexity" and r.citou_empresa for r in resultados
        )
        tem_perplexity = any(r.ia_nome == "perplexity" for r in resultados)
        if tem_perplexity and not perplexity_citou:
            acoes.append({
                "prioridade": "urgente",
                "acao": f"Publicar perfil em diretórios especializados de {request.segmento.value}",
            })

        if seo < 4:
            acoes.append({
                "prioridade": "30_dias",
                "acao": "Adicionar meta description única em todas as páginas",
            })
            acoes.append({
                "prioridade": "30_dias",
                "acao": "Criar sitemap.xml e submeter ao Google Search Console",
            })

        if conteudo < 4:
            acoes.append({
                "prioridade": "30_dias",
                "acao": f"Publicar 4 artigos de blog sobre {request.especialidade} em 30 dias",
            })

        concorrentes = self._extrair_concorrentes(resultados, request.empresa_nome)
        if concorrentes:
            nomes = ", ".join(c["nome"] for c in concorrentes[:3])
            acoes.append({
                "prioridade": "30_dias",
                "acao": f"Analisar presença digital de: {nomes}",
            })

        acoes.append({
            "prioridade": "continuo",
            "acao": "Monitoramento mensal de citação nas 4 IAs",
        })
        acoes.append({
            "prioridade": "continuo",
            "acao": f"Publicação quinzenal de conteúdo educativo sobre {request.especialidade}",
        })

        ordem = {"urgente": 0, "30_dias": 1, "continuo": 2}
        acoes.sort(key=lambda a: ordem.get(a["prioridade"], 9))
        return acoes

    async def estimar_custo(self, request: DiagnosticoRequest) -> dict:
        n = len(request.perguntas_ids)
        por_ia = {}
        total_usd = 0.0
        for nome in request.ias_ativas:
            svc = self.servicos.get(nome)
            if svc is None:
                continue
            est = svc.estimar_custo(n)
            por_ia[nome] = est
            total_usd += est["usd"]

        # tempo: ~0.5s/pergunta + overhead, Perplexity 1s
        tempo = 0
        for nome in request.ias_ativas:
            delay = 1.0 if nome == "perplexity" else 0.5
            tempo = max(tempo, int(n * delay + n * 2))

        return {
            "por_ia": por_ia,
            "total_usd": round(total_usd, 4),
            "total_brl": round(total_usd * 5.5, 2),
            "tempo_estimado_seg": tempo,
            "total_chamadas_api": n * len(request.ias_ativas),
        }

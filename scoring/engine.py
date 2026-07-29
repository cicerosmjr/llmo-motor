"""Engine de scoring LLMO — citação, dimensões e score geral."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from models.schemas import (
    Bloco1InterpretacaoEnum,
    Bloco1NotaIA,
    Bloco1Visibilidade,
    BlocoManual,
    CriterioManualNota,
    DiagnosticoPlanilha,
    DiagnosticoRequest,
    NivelCitacaoEnum,
    ResultadoIA,
    ScoreDimensao,
    ScoreTotalLLMO,
    StatusCriterioEnum,
    StatusEnum,
)
from scoring.gabarito_blocos import BLOCOS_MANUAIS_DEFINICAO, ids_criterios_validos


class ScoringEngine:
    PESOS_DIMENSAO = {
        "seo_tecnico": 0.25,
        "llmo_schema": 0.30,
        "autoridade_citacao": 0.25,
        "conteudo": 0.20,
    }

    PESOS_IA = {
        "chatgpt": 0.40,  # maior peso — share de uso no Brasil
        "gemini": 0.25,
        "perplexity": 0.20,  # peso menor; sinal diagnóstico de web real-time
        "claude": 0.15,
    }

    PONTUACAO_CITACAO = {
        "detalhado": 10.0,
        "superficial": 6.0,
        "vago": 3.0,
        "nao_citado": 0.0,
    }

    SEO_PONTOS = {
        "ssl": 1.5,
        "meta_description": 1.0,
        "canonical": 0.8,
        "viewport": 1.0,
        "sitemap": 1.5,
        "robots": 1.0,
        "open_graph": 0.8,
        "h1": 0.6,
        "conteudo_html": 1.8,
    }

    LLMO_PONTOS = {
        "schema_ld": 2.0,
        "faq_schema": 2.5,
        "local_business": 2.5,
        "llms_txt": 3.0,
        "open_graph_completo": 0.5,
    }

    CONTEUDO_PONTOS = {
        "h1_presente": 1.5,
        "estrutura_semantica": 1.5,
        "conteudo_substancial": 2.5,
        "blog_ativo": 2.5,
    }

    DETALHES_MARCADORES = (
        r"\b(?:rua|avenida|av\.|endereço|telefone|whatsapp|\(\d{2}\)|crm|oab|crp|"
        r"fundad[oa]|desde\s+\d{4}|prêmio|especialista|doutor|dra?\.)\b",
    )

    # Palavras genéricas demais para citação parcial isolada
    STOPWORDS_NOME = {
        "clinica", "clínica", "clinic", "escritorio", "escritório",
        "instituto", "centro", "hospital", "laboratorio", "laboratório",
        "empresa", "ltda", "sao", "são", "dos", "das", "del",
    }

    # Termos de especialidade — sozinhos não identificam a empresa
    ESPECIALIDADE_TOKENS = {
        "cirurgia", "plastica", "plástica", "dermatologia", "odontologia",
        "psiquiatria", "direito", "tributario", "tributário", "imobiliario",
        "imobiliário", "trabalhista", "patrimonial", "ansiedade", "depressao",
        "depressão", "psicologia", "infantil", "geral",
    }

    def avaliar_resposta(self, resposta: str, empresa_nome: str) -> dict[str, Any]:
        if not resposta or resposta.startswith("ERRO_"):
            return {
                "citou": False,
                "nivel": NivelCitacaoEnum.nao_citado.value,
                "pontuacao": 0.0,
                "trecho": None,
                "concorrentes": [],
            }

        texto = resposta
        nome = empresa_nome.strip()
        nome_lower = nome.lower()
        resp_lower = texto.lower()

        tokens = [
            p for p in re.split(r"\s+", nome_lower)
            if len(p) > 3 and p not in self.STOPWORDS_NOME
        ]
        brand_tokens = [t for t in tokens if t not in self.ESPECIALIDADE_TOKENS]
        citou_completo = nome_lower in resp_lower

        brand_hits = [t for t in brand_tokens if t in resp_lower]
        # Citação parcial (vaga): pelo menos um token de marca distintivo
        citou_parcial = bool(brand_hits) or (
            not brand_tokens and sum(1 for t in tokens if t in resp_lower) >= 2
        )

        if not citou_completo and not citou_parcial:
            return {
                "citou": False,
                "nivel": NivelCitacaoEnum.nao_citado.value,
                "pontuacao": 0.0,
                "trecho": None,
                "concorrentes": self._extrair_concorrentes_heuristica(texto, nome),
            }

        # Localiza trecho
        idx = resp_lower.find(nome_lower) if citou_completo else -1
        if idx < 0:
            for p in brand_hits or tokens:
                idx = resp_lower.find(p)
                if idx >= 0:
                    break
        ini = max(0, idx - 80)
        fim = min(len(texto), idx + len(nome) + 120)
        trecho = texto[ini:fim].strip() if idx >= 0 else None

        tem_detalhe = bool(re.search(self.DETALHES_MARCADORES[0], texto, re.I))
        if citou_completo and tem_detalhe:
            nivel = NivelCitacaoEnum.detalhado
        elif citou_completo:
            nivel = NivelCitacaoEnum.superficial
        else:
            nivel = NivelCitacaoEnum.vago

        return {
            "citou": True,
            "nivel": nivel.value,
            "pontuacao": self.PONTUACAO_CITACAO[nivel.value],
            "trecho": trecho[:200] if trecho else None,
            "concorrentes": self._extrair_concorrentes_heuristica(texto, nome),
        }

    def _extrair_concorrentes_heuristica(self, texto: str, empresa: str) -> list[str]:
        # Heurística simples: padrões "Clínica X", "Dr. Y"
        candidatos = re.findall(
            r"\b(?:Clínica|Clinic|Escritório|Dr\.|Dra\.|Instituto)\s+[A-ZÀ-Ú][\wÀ-ú\'\-]+(?:\s+[A-ZÀ-Ú][\wÀ-ú\'\-]+){0,3}",
            texto,
        )
        empresa_l = empresa.lower()
        out: list[str] = []
        for c in candidatos:
            if empresa_l not in c.lower() and c not in out:
                out.append(c)
        return out[:5]

    def calcular_score_autoridade(self, resultados: list[ResultadoIA]) -> ScoreDimensao:
        por_ia: dict[str, list[float]] = {}
        for r in resultados:
            por_ia.setdefault(r.ia_nome, []).append(r.pontuacao)

        medias: dict[str, float] = {
            ia: (sum(vals) / len(vals) if vals else 0.0) for ia, vals in por_ia.items()
        }

        # Normaliza pesos para IAs presentes
        pesos_usados = {ia: self.PESOS_IA.get(ia, 0.1) for ia in medias}
        total_peso = sum(pesos_usados.values()) or 1.0
        score = sum(medias[ia] * (pesos_usados[ia] / total_peso) for ia in medias)

        ias_citaram = [ia for ia, vals in por_ia.items() if any(v > 0 for v in vals)]
        ias_nao = [ia for ia in por_ia if ia not in ias_citaram]
        taxa = (
            sum(1 for r in resultados if r.citou_empresa) / len(resultados)
            if resultados
            else 0.0
        )

        return ScoreDimensao(
            nome="autoridade_citacao",
            peso=self.PESOS_DIMENSAO["autoridade_citacao"],
            pontuacao_bruta=round(score, 2),
            pontuacao_ponderada=round(score * self.PESOS_DIMENSAO["autoridade_citacao"], 2),
            detalhes={
                "por_ia": {k: round(v, 2) for k, v in medias.items()},
                "ias_que_citaram": ias_citaram,
                "ias_que_nao_citaram": ias_nao,
                "taxa_citacao_geral": round(taxa, 2),
            },
        )

    def calcular_score_seo(self, checks: dict[str, bool]) -> ScoreDimensao:
        bruta = sum(
            pts for chave, pts in self.SEO_PONTOS.items() if checks.get(chave)
        )
        bruta = min(bruta, 10.0)
        return ScoreDimensao(
            nome="seo_tecnico",
            peso=self.PESOS_DIMENSAO["seo_tecnico"],
            pontuacao_bruta=round(bruta, 2),
            pontuacao_ponderada=round(bruta * self.PESOS_DIMENSAO["seo_tecnico"], 2),
            detalhes={"checks": checks},
        )

    def calcular_score_llmo(
        self, checks: dict[str, bool], resultados: list[ResultadoIA]
    ) -> ScoreDimensao:
        bruta = sum(
            pts for chave, pts in self.LLMO_PONTOS.items() if checks.get(chave)
        )
        # Bônus Perplexity detalhado
        for r in resultados:
            if (
                r.ia_nome == "perplexity"
                and r.nivel_citacao == NivelCitacaoEnum.detalhado
            ):
                bruta += 1.0
                break
        bruta = min(bruta, 10.0)
        return ScoreDimensao(
            nome="llmo_schema",
            peso=self.PESOS_DIMENSAO["llmo_schema"],
            pontuacao_bruta=round(bruta, 2),
            pontuacao_ponderada=round(bruta * self.PESOS_DIMENSAO["llmo_schema"], 2),
            detalhes={"checks": checks},
        )

    def calcular_score_conteudo(self, checks: dict[str, bool]) -> ScoreDimensao:
        bruta = sum(
            pts for chave, pts in self.CONTEUDO_PONTOS.items() if checks.get(chave)
        )
        # Cap formal 10; max natural ~8.0 com os 4 checks
        bruta = min(bruta, 10.0)
        return ScoreDimensao(
            nome="conteudo",
            peso=self.PESOS_DIMENSAO["conteudo"],
            pontuacao_bruta=round(bruta, 2),
            pontuacao_ponderada=round(bruta * self.PESOS_DIMENSAO["conteudo"], 2),
            detalhes={"checks": checks},
        )

    def calcular_score_geral(
        self,
        seo: ScoreDimensao,
        llmo: ScoreDimensao,
        autoridade: ScoreDimensao,
        conteudo: ScoreDimensao,
    ) -> tuple[float, StatusEnum]:
        score = (
            seo.pontuacao_ponderada
            + llmo.pontuacao_ponderada
            + autoridade.pontuacao_ponderada
            + conteudo.pontuacao_ponderada
        )
        score = round(score, 2)
        if score < 3.0:
            status = StatusEnum.critico
        elif score < 5.0:
            status = StatusEnum.baixo
        elif score < 7.0:
            status = StatusEnum.medio
        elif score < 8.5:
            status = StatusEnum.bom
        else:
            status = StatusEnum.excelente
        return score, status

    def gerar_resumo_executivo(
        self,
        request: DiagnosticoRequest,
        score_geral: float,
        status: StatusEnum,
        scores: dict[str, ScoreDimensao],
        concorrentes: list[dict],
    ) -> str:
        autoridade = scores.get("autoridade_citacao")
        ias_citaram = (
            autoridade.detalhes.get("ias_que_citaram", []) if autoridade else []
        )
        n_ias = len(request.ias_ativas)
        dim_baixa = min(
            scores.values(),
            key=lambda s: s.pontuacao_bruta,
            default=None,
        )
        gap = dim_baixa.nome if dim_baixa else "não identificado"
        conc = concorrentes[0]["nome"] if concorrentes else "Nenhum concorrente destacado"
        return (
            f"{request.empresa_nome} obteve score {score_geral}/10 — {status.value.upper()}. "
            f"{n_ias} IAs testadas, {len(ias_citaram)} citaram a empresa. "
            f"Principal gap: {gap}. {conc} lidera as menções concorrentes."
        )

    # ── Bloco 1 — Visibilidade nas IAs (planilha) ──

    # Nota conservadora (limite inferior do gabarito da planilha)
    NOTA_POR_RODADA = {
        "r1": 7.0,
        "r2": 7.0,
        "r3": 6.0,
        "r4": 2.0,
        "r5": 9.0,
    }

    IAS_BLOCO1 = ("chatgpt", "gemini", "claude", "perplexity")

    def calcular_bloco1_visibilidade(
        self,
        resultados: list[ResultadoIA],
        mapa_rodada: dict[UUID, str],
        ias_ativas: list[str] | None = None,
    ) -> Bloco1Visibilidade:
        """
        Média simples das notas por IA, derivadas das rodadas R1–R5.

        - Rodada conta como aparição se qualquer pergunta do grupo citar a empresa.
        - Nota final da IA = menor nota entre as rodadas com aparição (ou 0).
        - IA com todas as respostas ERRO_ é marcada indisponível e excluída da média.
        """
        ias = [ia for ia in (ias_ativas or list(self.IAS_BLOCO1)) if ia in self.IAS_BLOCO1]
        if not ias:
            ias = list(self.IAS_BLOCO1)

        por_ia_raw: dict[str, list[ResultadoIA]] = {}
        for r in resultados:
            if r.ia_nome not in ias:
                continue
            por_ia_raw.setdefault(r.ia_nome, []).append(r)

        notas: list[Bloco1NotaIA] = []
        validas: list[float] = []
        indisponiveis: list[str] = []

        for ia in ias:
            items = por_ia_raw.get(ia, [])
            if not items:
                notas.append(
                    Bloco1NotaIA(
                        ia_nome=ia,
                        nota=None,
                        disponivel=False,
                        motivo="sem_respostas",
                    )
                )
                indisponiveis.append(ia)
                continue

            # Todas falharam tecnicamente → indisponível (não conta como 0)
            if all((r.resposta_completa or "").startswith("ERRO_") for r in items):
                notas.append(
                    Bloco1NotaIA(
                        ia_nome=ia,
                        nota=None,
                        disponivel=False,
                        motivo="erro_tecnico",
                    )
                )
                indisponiveis.append(ia)
                continue

            rodadas_hit: set[str] = set()
            evidencias: list[str] = []
            for r in items:
                if not r.citou_empresa:
                    continue
                rodada = mapa_rodada.get(r.pergunta_id)
                if not rodada:
                    continue
                rodadas_hit.add(rodada)
                trecho = (r.trecho_relevante or r.pergunta_texto or "")[:120]
                evidencias.append(f"{rodada.upper()}: {trecho}")

            if not rodadas_hit:
                nota = 0.0
                motivo = "nao_apareceu"
            else:
                valores = [
                    self.NOTA_POR_RODADA[r]
                    for r in rodadas_hit
                    if r in self.NOTA_POR_RODADA
                ]
                nota = min(valores) if valores else 0.0
                motivo = "menor_nota_rodadas"

            notas.append(
                Bloco1NotaIA(
                    ia_nome=ia,
                    nota=nota,
                    disponivel=True,
                    rodadas_com_aparicao=sorted(rodadas_hit),
                    evidencias=evidencias[:8],
                    motivo=motivo,
                )
            )
            validas.append(nota)

        if validas:
            media = round(sum(validas) / len(validas), 2)
            interpretacao, label = self._interpretar_bloco1(media)
        else:
            media = None
            interpretacao = Bloco1InterpretacaoEnum.indisponivel
            label = "Indisponível"

        return Bloco1Visibilidade(
            por_ia=notas,
            media=media,
            interpretacao=interpretacao,
            interpretacao_label=label,
            ias_avaliadas=len(validas),
            ias_indisponiveis=indisponiveis,
        )

    def _interpretar_bloco1(
        self, media: float
    ) -> tuple[Bloco1InterpretacaoEnum, str]:
        if media <= 3:
            return Bloco1InterpretacaoEnum.invisivel, "Invisível nas IAs"
        if media <= 5:
            return Bloco1InterpretacaoEnum.existencia_basica, "Existência básica"
        if media <= 7:
            return (
                Bloco1InterpretacaoEnum.buscas_especificas,
                "Aparece em buscas específicas",
            )
        if media <= 9:
            return (
                Bloco1InterpretacaoEnum.recomendacao_ativa,
                "Recomendado ativamente",
            )
        return (
            Bloco1InterpretacaoEnum.referencia_dominante,
            "Referência dominante no nicho",
        )

    # ── Blocos manuais 2–6 + SCORE TOTAL (planilha) ──

    @staticmethod
    def status_criterio(nota: float | None) -> StatusCriterioEnum:
        if nota is None:
            return StatusCriterioEnum.preencher
        if nota >= 7:
            return StatusCriterioEnum.ok
        if nota >= 4:
            return StatusCriterioEnum.parcial
        return StatusCriterioEnum.ausente

    def calcular_blocos_manuais_e_total(
        self,
        bloco1_media: float | None,
        notas: dict[str, float | None] | None = None,
    ) -> DiagnosticoPlanilha:
        """
        Monta blocos 2–6 a partir das notas manuais e calcula SCORE TOTAL.

        - Média do bloco = AVERAGE só das notas preenchidas (vazio ignorado).
        - Bloco sem nenhuma nota → media=None e não entra no total.
        - SCORE TOTAL = média das médias dos blocos disponíveis (inclui Bloco 1 se houver).
        """
        notas = dict(notas or {})
        validos = ids_criterios_validos()
        # Descarta ids desconhecidos
        notas = {k: v for k, v in notas.items() if k in validos}

        blocos: list[BlocoManual] = []
        medias_por_bloco: dict[str, float | None] = {"bloco1": bloco1_media}

        for defn in BLOCOS_MANUAIS_DEFINICAO:
            criterios: list[CriterioManualNota] = []
            preenchidas: list[float] = []
            for c in defn["criterios"]:
                nota = notas.get(c["id"])
                if nota is not None:
                    preenchidas.append(float(nota))
                criterios.append(
                    CriterioManualNota(
                        criterio_id=c["id"],
                        label=c["label"],
                        nota=nota,
                        status=self.status_criterio(nota),
                        como_verificar=c.get("como_verificar", ""),
                        gabarito=c.get("gabarito", ""),
                    )
                )
            media_bloco = (
                round(sum(preenchidas) / len(preenchidas), 4) if preenchidas else None
            )
            medias_por_bloco[defn["id"]] = media_bloco
            blocos.append(
                BlocoManual(
                    id=defn["id"],
                    numero=defn["numero"],
                    titulo=defn["titulo"],
                    criterios=criterios,
                    media=round(media_bloco, 2) if media_bloco is not None else None,
                )
            )

        # SCORE TOTAL: média das médias disponíveis (como AVERAGE(D8,D13,...))
        no_calculo: list[str] = []
        valores: list[float] = []
        if bloco1_media is not None:
            no_calculo.append("bloco1")
            valores.append(float(bloco1_media))
        for defn in BLOCOS_MANUAIS_DEFINICAO:
            m = medias_por_bloco.get(defn["id"])
            if m is not None:
                no_calculo.append(defn["id"])
                valores.append(float(m))

        if valores:
            media_total = round(sum(valores) / len(valores), 2)
            interp, label = self._interpretar_bloco1(media_total)
        else:
            media_total = None
            interp = Bloco1InterpretacaoEnum.indisponivel
            label = "Indisponível"

        score_total = ScoreTotalLLMO(
            media=media_total,
            interpretacao=interp,
            interpretacao_label=label,
            medias_por_bloco={
                k: (round(v, 2) if v is not None else None)
                for k, v in medias_por_bloco.items()
            },
            blocos_no_calculo=no_calculo,
        )

        return DiagnosticoPlanilha(
            blocos_manuais=blocos,
            score_total=score_total,
            notas_salvas=notas,
        )

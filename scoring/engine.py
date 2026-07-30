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
from scoring.gabarito_blocos import blocos_para_segmento, ids_criterios_validos


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

    # Escala planilha: 0 / 2 / 5 / 7 / 9 / 10
    PONTUACAO_CITACAO = {
        "nao_citado": 0.0,
        "nome_direto": 2.0,
        "mencao": 5.0,
        "recomendado": 7.0,
        "autoridade": 9.0,
        "referencia": 10.0,
        "erro_api": 0.0,
        # legado (jobs antigos)
        "detalhado": 10.0,
        "superficial": 6.0,
        "vago": 3.0,
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

    # Recusa / desconhecimento — NÃO é citação positiva
    NEGACAO_PADROES = re.compile(
        r"(?i)(?:"
        r"n[aã]o\s+(?:tenho|encontrei|possuo|conhe[cç]o|localizei|identifiquei|"
        r"encontrei\s+nenhum|achei|há\s+registros?\s+p[uú]blicos)|"
        r"n[aã]o\s+(?:posso|consigo)\s+confirmar|"
        r"n[aã]o\s+(?:seria|é)\s+(?:responsável|apropriado)|"
        r"n[aã]o\s+posso\s+confirmar\s+(?:sua\s+)?exist[eê]ncia|"
        r"sem\s+(?:informa[cç][oõ]es|dados)\s+(?:confi[aá]veis|espec[ií]ficas|atualizadas)|"
        r"n[aã]o\s+tenho\s+(?:informa[cç][oõ]es|dados)\s+"
        r"(?:confi[aá]veis|atualizadas|espec[ií]ficas)|"
        r"desconhe[cç]o|"
        r"n[aã]o\s+tenho\s+como\s+(?:verificar|confirmar)|"
        r"n[aã]o\s+seria\s+(?:respons[aá]vel\s+)?recomendar"
        r")"
    )

    RECOMENDACAO_PADROES = re.compile(
        r"(?i)\b(?:recomendo|recomendar|indicação|indico|destaque|referência|"
        r"melhor\s+op[cç][aã]o|altamente\s+recomendad[oa]|vale\s+a\s+pena)\b"
    )

    # Palavras genéricas demais para citação parcial isolada
    STOPWORDS_NOME = {
        "clinica", "clínica", "clinic", "escritorio", "escritório",
        "instituto", "centro", "hospital", "laboratorio", "laboratório",
        "empresa", "ltda", "sao", "são", "dos", "das", "del",
        "advocacia", "advogados", "associados", "associado",
    }

    # Termos de especialidade — sozinhos não identificam a empresa
    ESPECIALIDADE_TOKENS = {
        "cirurgia", "plastica", "plástica", "dermatologia", "odontologia",
        "psiquiatria", "direito", "tributario", "tributário", "imobiliario",
        "imobiliário", "trabalhista", "patrimonial", "ansiedade", "depressao",
        "depressão", "psicologia", "infantil", "geral",
    }

    def avaliar_resposta(
        self,
        resposta: str,
        empresa_nome: str,
        rodada: str | None = None,
    ) -> dict[str, Any]:
        """
        Avalia citação com escala 0/2/5/7/9/10 e teto por rodada.

        - R4 (nome direto): máximo nome_direto (2), nunca 7–10.
        - Negação / desconhecimento → nao_citado (0).
        - Marca parcial (só parte do nome) com 2+ tokens de marca → nao_citado.
        - ERRO_* → erro_api (excluído das médias de autoridade).
        """
        if not resposta:
            return self._resultado_avaliacao(
                False, NivelCitacaoEnum.nao_citado, concorrentes=[]
            )
        if resposta.startswith("ERRO_"):
            return self._resultado_avaliacao(
                False, NivelCitacaoEnum.erro_api, concorrentes=[]
            )

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

        # Com 2+ tokens de marca, exige nome completo (evita "Oliveira Advocacia"
        # bater em "Oliveira Leite Advocacia").
        if len(brand_tokens) >= 2:
            citou_parcial = False
        else:
            brand_hits = [t for t in brand_tokens if t in resp_lower]
            citou_parcial = bool(brand_hits) or (
                not brand_tokens and sum(1 for t in tokens if t in resp_lower) >= 2
            )

        concorrentes = self._extrair_concorrentes_heuristica(texto, nome)

        if not citou_completo and not citou_parcial:
            return self._resultado_avaliacao(
                False, NivelCitacaoEnum.nao_citado, concorrentes=concorrentes
            )

        # Negação / recusa: nome no texto sem reconhecimento real
        if self.NEGACAO_PADROES.search(texto):
            return self._resultado_avaliacao(
                False, NivelCitacaoEnum.nao_citado, concorrentes=concorrentes
            )

        idx = resp_lower.find(nome_lower) if citou_completo else -1
        if idx < 0 and citou_parcial:
            for p in brand_tokens or tokens:
                idx = resp_lower.find(p)
                if idx >= 0:
                    break
        ini = max(0, idx - 80)
        fim = min(len(texto), idx + len(nome) + 120)
        trecho = texto[ini:fim].strip() if idx >= 0 else None

        tem_detalhe = bool(re.search(self.DETALHES_MARCADORES[0], texto, re.I))
        parece_principal = bool(self.RECOMENDACAO_PADROES.search(texto)) or (
            citou_completo and idx >= 0 and idx < 200
        )

        nivel = self._nivel_por_rodada(
            rodada=rodada,
            citou_completo=citou_completo,
            tem_detalhe=tem_detalhe,
            parece_principal=parece_principal,
        )

        return self._resultado_avaliacao(
            True, nivel, trecho=trecho[:200] if trecho else None, concorrentes=concorrentes
        )

    def _resultado_avaliacao(
        self,
        citou: bool,
        nivel: NivelCitacaoEnum,
        trecho: str | None = None,
        concorrentes: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "citou": citou,
            "nivel": nivel.value,
            "pontuacao": self.PONTUACAO_CITACAO[nivel.value],
            "trecho": trecho,
            "concorrentes": concorrentes or [],
        }

    def _nivel_por_rodada(
        self,
        rodada: str | None,
        citou_completo: bool,
        tem_detalhe: bool,
        parece_principal: bool,
    ) -> NivelCitacaoEnum:
        """Mapeia rodada + qualidade → nível da escala 0/2/5/7/9/10."""
        r = (rodada or "").lower().strip()

        # R4: busca pelo nome — teto absoluto = 2
        if r == "r4":
            return NivelCitacaoEnum.nome_direto

        # Citação parcial (1 token) sem nome completo → no máximo menção
        if not citou_completo:
            return NivelCitacaoEnum.mencao

        if r == "r3":
            return (
                NivelCitacaoEnum.recomendado
                if tem_detalhe or parece_principal
                else NivelCitacaoEnum.mencao
            )

        if r in ("r1", "r2"):
            if tem_detalhe and parece_principal:
                return NivelCitacaoEnum.autoridade
            if tem_detalhe or parece_principal:
                return NivelCitacaoEnum.recomendado
            return NivelCitacaoEnum.mencao

        if r == "r5":
            if tem_detalhe or parece_principal:
                return NivelCitacaoEnum.referencia
            return NivelCitacaoEnum.autoridade

        # Sem rodada: qualidade pura na escala nova
        if tem_detalhe and parece_principal:
            return NivelCitacaoEnum.referencia
        if tem_detalhe:
            return NivelCitacaoEnum.autoridade
        if parece_principal:
            return NivelCitacaoEnum.recomendado
        return NivelCitacaoEnum.mencao

    # Indicadores de logradouro — "R. Dr. Gilberto Studart" não é concorrente
    ENDERECO_ANTES = re.compile(
        r"(?i)(?:^|[\s,;])(?:rua|r\.|av\.|avenida|alameda|travessa|trav\.|"
        r"rodovia|estrada|praça|praca|largo|viela)\s*$"
    )
    ENDERECO_DEPOIS = re.compile(
        r"^\s*,?\s*(?:n[ºo°.]?\s*)?\d{1,5}\b",
        re.I,
    )

    def _extrair_concorrentes_heuristica(self, texto: str, empresa: str) -> list[str]:
        """Extrai clínicas, Drs. e bancas/escritórios (ex.: X & Y Advogados)."""
        padroes = [
            # Prefixo institucional / Dr.
            r"\b(?:Clínica|Clinic|Escritório|Instituto|Dr\.|Dra\.)\s+"
            r"[A-ZÀ-Ú][\wÀ-ú\'\-]+(?:\s+[A-ZÀ-Ú][\wÀ-ú\'\-]+){0,4}",
            # Banca: Nome & Nome Advogados / Advocacia
            r"\b[A-ZÀ-Ú][\wÀ-ú\'\-]+(?:\s+(?:&|e)\s+[A-ZÀ-Ú][\wÀ-ú\'\-]+)+"
            r"\s+(?:Advogados|Advocacia|Associados)\b",
            # Nome Advogados / Advocacia / Associados
            r"\b[A-ZÀ-Ú][\wÀ-ú\'\-]+(?:\s+[A-ZÀ-Ú][\wÀ-ú\'\-]+){0,3}\s+"
            r"(?:Advogados|Advocacia|Associados)\b",
        ]
        empresa_l = empresa.lower()
        out: list[str] = []
        for padrao in padroes:
            for m in re.finditer(padrao, texto):
                nome = m.group(0).strip().rstrip(".,;")
                if empresa_l in nome.lower():
                    continue
                if self._parece_endereco(texto, m.start(), m.end()):
                    continue
                if nome not in out:
                    out.append(nome)
        return out[:15]

    def _parece_endereco(self, texto: str, inicio: int, fim: int) -> bool:
        """True se o match está em logradouro (ex.: R. Dr. Gilberto Studart, 55)."""
        prefixo = texto[max(0, inicio - 24) : inicio]
        if self.ENDERECO_ANTES.search(prefixo):
            return True
        sufixo = texto[fim : fim + 20]
        if self.ENDERECO_DEPOIS.match(sufixo):
            # Só descarta Dr./Dra. seguido de número (padrão de rua)
            trecho = texto[inicio:fim]
            if re.match(r"(?i)^dra?\.\s+", trecho):
                return True
        return False

    def calcular_score_autoridade(self, resultados: list[ResultadoIA]) -> ScoreDimensao:
        por_ia: dict[str, list[float]] = {}
        ias_erro: set[str] = set()
        ias_com_dado: set[str] = set()

        for r in resultados:
            # ERRO_API não dilui a média — é dado ausente
            if (
                r.nivel_citacao == NivelCitacaoEnum.erro_api
                or (r.resposta_completa or "").startswith("ERRO_")
            ):
                ias_erro.add(r.ia_nome)
                continue
            ias_com_dado.add(r.ia_nome)
            por_ia.setdefault(r.ia_nome, []).append(r.pontuacao)

        medias: dict[str, float] = {
            ia: (sum(vals) / len(vals) if vals else 0.0) for ia, vals in por_ia.items()
        }

        # IAs só com erro técnico: fora do peso (não contam como 0)
        pesos_usados = {ia: self.PESOS_IA.get(ia, 0.1) for ia in medias}
        total_peso = sum(pesos_usados.values()) or 1.0
        score = (
            sum(medias[ia] * (pesos_usados[ia] / total_peso) for ia in medias)
            if medias
            else 0.0
        )

        ias_citaram = [ia for ia, vals in por_ia.items() if any(v > 0 for v in vals)]
        ias_nao = [ia for ia in por_ia if ia not in ias_citaram]
        validos = [
            r
            for r in resultados
            if r.nivel_citacao != NivelCitacaoEnum.erro_api
            and not (r.resposta_completa or "").startswith("ERRO_")
        ]
        taxa = (
            sum(1 for r in validos if r.citou_empresa) / len(validos) if validos else 0.0
        )
        so_erro = sorted(ias_erro - ias_com_dado)

        return ScoreDimensao(
            nome="autoridade_citacao",
            peso=self.PESOS_DIMENSAO["autoridade_citacao"],
            pontuacao_bruta=round(score, 2),
            pontuacao_ponderada=round(score * self.PESOS_DIMENSAO["autoridade_citacao"], 2),
            detalhes={
                "por_ia": {k: round(v, 2) for k, v in medias.items()},
                "ias_que_citaram": ias_citaram,
                "ias_que_nao_citaram": ias_nao,
                "ias_erro_api": so_erro,
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
        # Bônus Perplexity com citação forte (autoridade/referência)
        niveis_fortes = {
            NivelCitacaoEnum.referencia,
            NivelCitacaoEnum.autoridade,
            NivelCitacaoEnum.detalhado,
        }
        for r in resultados:
            if r.ia_nome == "perplexity" and r.nivel_citacao in niveis_fortes:
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
        segmento: str | None = None,
    ) -> DiagnosticoPlanilha:
        """
        Monta blocos 2–6 a partir das notas manuais e calcula SCORE TOTAL.

        - Média do bloco = AVERAGE só das notas preenchidas (vazio ignorado).
        - Bloco sem nenhuma nota → media=None e não entra no total.
        - SCORE TOTAL = média das médias dos blocos disponíveis (inclui Bloco 1 se houver).
        - Critérios com restrição de segmento (ex.: Doctoralia) só entram se aplicáveis.
        """
        notas = dict(notas or {})
        definicao = blocos_para_segmento(segmento)
        validos = ids_criterios_validos(segmento)
        # Descarta ids desconhecidos ou fora do segmento
        notas = {k: v for k, v in notas.items() if k in validos}

        blocos: list[BlocoManual] = []
        medias_por_bloco: dict[str, float | None] = {"bloco1": bloco1_media}

        for defn in definicao:
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
        for defn in definicao:
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

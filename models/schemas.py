"""Modelos Pydantic v2 do sistema LLMO Vértice Carioca."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, HttpUrl


class CategoriaEnum(str, Enum):
    reconhecimento = "reconhecimento"
    recomendacao = "recomendacao"
    reputacao = "reputacao"
    servicos = "servicos"
    localizacao = "localizacao"
    generica = "generica"


class SegmentoEnum(str, Enum):
    medicina = "medicina"
    advocacia = "advocacia"
    psicologia = "psicologia"
    odontologia = "odontologia"
    outro = "outro"


class NivelCitacaoEnum(str, Enum):
    """Escala de citação 0/2/5/7/9/10 (+ erro_api e aliases legados)."""

    nao_citado = "nao_citado"  # 0
    nome_direto = "nome_direto"  # 2 — só em busca pelo nome (R4)
    mencao = "mencao"  # 5
    recomendado = "recomendado"  # 7
    autoridade = "autoridade"  # 9
    referencia = "referencia"  # 10
    erro_api = "erro_api"  # dado ausente (cota/falha) — não entra na média
    # Aliases legados (jobs antigos)
    detalhado = "detalhado"
    superficial = "superficial"
    vago = "vago"


# Labels exibidos no painel/relatório
LABEL_NIVEL_CITACAO: dict[str, str] = {
    "nao_citado": "não citado (0)",
    "nome_direto": "nome direto (2)",
    "mencao": "menção (5)",
    "recomendado": "recomendado (7)",
    "autoridade": "autoridade (9)",
    "referencia": "referência (10)",
    "erro_api": "erro de API",
    # legado
    "detalhado": "citado detalhado",
    "superficial": "citado",
    "vago": "vago",
}


def label_nivel_citacao(nivel: NivelCitacaoEnum | str) -> str:
    chave = nivel.value if isinstance(nivel, NivelCitacaoEnum) else str(nivel)
    return LABEL_NIVEL_CITACAO.get(chave, chave)


class StatusEnum(str, Enum):
    critico = "critico"
    baixo = "baixo"
    medio = "medio"
    bom = "bom"
    excelente = "excelente"


class RodadaEnum(str, Enum):
    """Rodadas do teste de visibilidade (Bloco 1 da planilha LLMO)."""

    r1 = "r1"  # genérica (sem nome)
    r2 = "r2"  # intenção real
    r3 = "r3"  # por bairro
    r4 = "r4"  # nome direto
    r5 = "r5"  # comparação / lista


class Bloco1InterpretacaoEnum(str, Enum):
    invisivel = "invisivel"
    existencia_basica = "existencia_basica"
    buscas_especificas = "buscas_especificas"
    recomendacao_ativa = "recomendacao_ativa"
    referencia_dominante = "referencia_dominante"
    indisponivel = "indisponivel"


class Pergunta(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    texto: str
    segmento: str
    especialidade: str | None = None
    categoria: CategoriaEnum
    rodada: RodadaEnum | None = None
    ativa: bool = True
    criada_em: datetime = Field(default_factory=datetime.utcnow)
    criada_por: str = "vertice"


class BancoPerguntasQuery(BaseModel):
    segmento: str | None = None
    especialidade: str | None = None
    categoria: CategoriaEnum | None = None
    apenas_ativas: bool = True
    busca_texto: str | None = None


class DiagnosticoRequest(BaseModel):
    empresa_nome: str
    empresa_razao_social: str | None = None
    site_url: str | None = None
    segmento: SegmentoEnum
    especialidade: str
    cidade: str
    bairro: str | None = None
    estado: str = "RJ"
    perguntas_ids: list[UUID]
    ias_ativas: list[str] = Field(
        default_factory=lambda: ["claude", "chatgpt", "gemini", "perplexity"]
    )

    @field_validator("site_url")
    @classmethod
    def validar_url(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("site_url deve ser uma URL válida (http/https)")
        # Valida formato via HttpUrl sem alterar o tipo do campo
        HttpUrl(v)
        return v

    @field_validator("bairro")
    @classmethod
    def normalizar_bairro(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("perguntas_ids")
    @classmethod
    def validar_qtd_perguntas(cls, v: list[UUID]) -> list[UUID]:
        if len(v) < 5 or len(v) > 20:
            raise ValueError("perguntas_ids deve ter entre 5 e 20 itens")
        return v


class ResultadoIA(BaseModel):
    ia_nome: str
    pergunta_id: UUID
    pergunta_texto: str
    resposta_completa: str
    citou_empresa: bool
    nivel_citacao: NivelCitacaoEnum
    pontuacao: float
    trecho_relevante: str | None = None
    concorrentes_citados: list[str] = Field(default_factory=list)

    @field_validator("pontuacao")
    @classmethod
    def validar_pontuacao(cls, v: float) -> float:
        if v < 0 or v > 10:
            raise ValueError("pontuacao deve estar entre 0 e 10")
        return v


class ScoreDimensao(BaseModel):
    nome: str
    peso: float
    pontuacao_bruta: float
    pontuacao_ponderada: float
    detalhes: dict[str, Any] = Field(default_factory=dict)


class Bloco1NotaIA(BaseModel):
    ia_nome: str
    nota: float | None = None
    disponivel: bool = True
    rodadas_com_aparicao: list[str] = Field(default_factory=list)
    evidencias: list[str] = Field(default_factory=list)
    motivo: str | None = None


class Bloco1Visibilidade(BaseModel):
    """Score paralelo — média simples das notas por IA (planilha Bloco 1)."""

    por_ia: list[Bloco1NotaIA] = Field(default_factory=list)
    media: float | None = None
    interpretacao: Bloco1InterpretacaoEnum = Bloco1InterpretacaoEnum.indisponivel
    interpretacao_label: str = "Indisponível"
    ias_avaliadas: int = 0
    ias_indisponiveis: list[str] = Field(default_factory=list)


class StatusCriterioEnum(str, Enum):
    preencher = "preencher"
    ok = "ok"
    parcial = "parcial"
    ausente = "ausente"


class CriterioManualNota(BaseModel):
    criterio_id: str
    label: str
    nota: float | None = None
    status: StatusCriterioEnum = StatusCriterioEnum.preencher
    como_verificar: str = ""
    gabarito: str = ""

    @field_validator("nota")
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v < 0 or v > 10:
            raise ValueError("nota deve estar entre 0 e 10")
        return v


class BlocoManual(BaseModel):
    id: str
    numero: int
    titulo: str
    criterios: list[CriterioManualNota] = Field(default_factory=list)
    media: float | None = None


class ScoreTotalLLMO(BaseModel):
    """Média das médias dos blocos disponíveis (planilha C36) — métrica paralela."""

    media: float | None = None
    interpretacao: Bloco1InterpretacaoEnum = Bloco1InterpretacaoEnum.indisponivel
    interpretacao_label: str = "Indisponível"
    medias_por_bloco: dict[str, float | None] = Field(default_factory=dict)
    blocos_no_calculo: list[str] = Field(default_factory=list)


class DiagnosticoPlanilha(BaseModel):
    """Diagnóstico no formato da planilha LLMO (blocos 1–6 + total)."""

    blocos_manuais: list[BlocoManual] = Field(default_factory=list)
    score_total: ScoreTotalLLMO | None = None
    notas_salvas: dict[str, float | None] = Field(default_factory=dict)


class BlocosManuaisUpdate(BaseModel):
    """Payload: criterio_id -> nota (null limpa)."""

    notas: dict[str, float | None] = Field(default_factory=dict)

    @field_validator("notas")
    @classmethod
    def validar_notas(
        cls, v: dict[str, float | None]
    ) -> dict[str, float | None]:
        for k, nota in v.items():
            if nota is None:
                continue
            if nota < 0 or nota > 10:
                raise ValueError(f"nota de {k} deve estar entre 0 e 10")
        return v


class DiagnosticoResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    request: DiagnosticoRequest
    resultados_ias: list[ResultadoIA]
    scores: dict[str, ScoreDimensao]
    score_geral: float
    status: StatusEnum
    concorrentes_mais_citados: list[dict[str, Any]] = Field(default_factory=list)
    plano_acao: list[dict[str, Any]] = Field(default_factory=list)
    resumo_executivo: str = ""
    bloco1_visibilidade: Bloco1Visibilidade | None = None
    diagnostico_planilha: DiagnosticoPlanilha | None = None


class EmpresaCliente(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    empresa_nome: str
    segmento: str
    especialidade: str
    site_url: str | None = None
    cidade: str
    estado: str
    diagnosticos: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ultima_atualizacao: datetime = Field(default_factory=datetime.utcnow)


class PerguntaCreate(BaseModel):
    texto: str
    segmento: str
    categoria: CategoriaEnum
    especialidade: str | None = None
    rodada: RodadaEnum | None = None


class PerguntaUpdate(BaseModel):
    texto: str | None = None
    segmento: str | None = None
    categoria: CategoriaEnum | None = None
    especialidade: str | None = None
    rodada: RodadaEnum | None = None
    ativa: bool | None = None

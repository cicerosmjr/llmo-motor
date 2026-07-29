"""Testes do sistema LLMO Vértice."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Credenciais de teste antes de importar a app
os.environ.setdefault("PAINEL_USUARIO", "catia")
os.environ.setdefault("PAINEL_SENHA", "teste12345678")

from models.schemas import (  # noqa: E402
    DiagnosticoRequest,
    DiagnosticoResult,
    NivelCitacaoEnum,
    ResultadoIA,
    ScoreDimensao,
    SegmentoEnum,
    StatusEnum,
)
from prompts.banco import BancoPerguntas  # noqa: E402
from prompts.substituidor import substituir_placeholders  # noqa: E402
from report.generator import ReportGenerator  # noqa: E402
from scoring.engine import ScoringEngine  # noqa: E402
from tests.mock_responses import (  # noqa: E402
    MOCK_EMPRESA,
    mock_citado_detalhado,
    mock_citado_superficial,
    mock_nao_citado,
    mock_vago,
)


@pytest.fixture
def empresa_request() -> DiagnosticoRequest:
    return DiagnosticoRequest(
        empresa_nome=MOCK_EMPRESA,
        segmento=SegmentoEnum.medicina,
        especialidade="cirurgia plástica",
        cidade="Rio de Janeiro",
        estado="RJ",
        perguntas_ids=[uuid4() for _ in range(10)],
        ias_ativas=["claude", "chatgpt", "gemini", "perplexity"],
    )


@pytest.fixture
def resultado_critico(empresa_request) -> DiagnosticoResult:
    return DiagnosticoResult(
        request=empresa_request,
        resultados_ias=[],
        scores={
            "seo_tecnico": ScoreDimensao(
                nome="seo_tecnico", peso=0.25, pontuacao_bruta=1.0, pontuacao_ponderada=0.25
            ),
            "llmo_schema": ScoreDimensao(
                nome="llmo_schema", peso=0.30, pontuacao_bruta=1.0, pontuacao_ponderada=0.30
            ),
            "autoridade_citacao": ScoreDimensao(
                nome="autoridade_citacao",
                peso=0.25,
                pontuacao_bruta=0.0,
                pontuacao_ponderada=0.0,
            ),
            "conteudo": ScoreDimensao(
                nome="conteudo", peso=0.20, pontuacao_bruta=2.0, pontuacao_ponderada=0.40
            ),
        },
        score_geral=1.8,
        status=StatusEnum.critico,
        resumo_executivo="Crítico",
    )


@pytest.fixture
def resultado_bom(empresa_request) -> DiagnosticoResult:
    return DiagnosticoResult(
        request=empresa_request,
        resultados_ias=[],
        scores={
            "seo_tecnico": ScoreDimensao(
                nome="seo_tecnico", peso=0.25, pontuacao_bruta=8.0, pontuacao_ponderada=2.0
            ),
            "llmo_schema": ScoreDimensao(
                nome="llmo_schema", peso=0.30, pontuacao_bruta=7.0, pontuacao_ponderada=2.1
            ),
            "autoridade_citacao": ScoreDimensao(
                nome="autoridade_citacao",
                peso=0.25,
                pontuacao_bruta=8.0,
                pontuacao_ponderada=2.0,
            ),
            "conteudo": ScoreDimensao(
                nome="conteudo", peso=0.20, pontuacao_bruta=7.0, pontuacao_ponderada=1.4
            ),
        },
        score_geral=7.5,
        status=StatusEnum.bom,
        resumo_executivo="Bom",
    )


# ── Banco ──


def test_banco_seed_carrega(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    banco = BancoPerguntas()
    assert len(banco._perguntas) >= 50


def test_banco_filtro_segmento(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    from models.schemas import BancoPerguntasQuery

    banco = BancoPerguntas()
    lista = banco.listar(BancoPerguntasQuery(segmento="medicina"))
    assert lista
    assert all(p.segmento == "medicina" for p in lista)


def test_banco_filtro_especialidade(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    from models.schemas import BancoPerguntasQuery

    banco = BancoPerguntas()
    lista = banco.listar(
        BancoPerguntasQuery(segmento="medicina", especialidade="cirurgia plástica")
    )
    assert lista
    assert all(
        p.especialidade and p.especialidade.lower() == "cirurgia plástica" for p in lista
    )


def test_banco_sugestao_equilibrada(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    banco = BancoPerguntas()
    sug = banco.sugerir_para_diagnostico("medicina", "cirurgia plástica", limite=10)
    assert len(sug) == 10
    cats = {p.categoria.value for p in sug}
    principais = {"reconhecimento", "recomendacao", "reputacao", "servicos"}
    assert len(cats & principais) >= 1


def test_banco_crud_ciclo_completo(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    # Usa banco real; cria e desativa
    banco = BancoPerguntas()
    p = banco.criar(
        texto="Teste {empresa} em {cidade}",
        segmento="medicina",
        categoria="generica",
        especialidade="teste",
    )
    banco.atualizar(p.id, {"texto": "Editado {empresa}"})
    banco.desativar(p.id)
    from models.schemas import BancoPerguntasQuery

    ativas = banco.listar(BancoPerguntasQuery(busca_texto="Editado", apenas_ativas=True))
    assert all(x.id != p.id for x in ativas)
    banco.deletar(p.id)


# ── Substituidor ──


def test_substituidor_sem_placeholders_residuais():
    texto = "A {empresa} em {cidade}/{estado} faz {especialidade} — {site_url}"
    out = substituir_placeholders(
        texto, "ACME", "dermato", "Rio", "RJ", site_url="https://acme.com"
    )
    assert "{" not in out
    assert "ACME" in out


def test_substituidor_cidade_bairro_empresa():
    texto = (
        "Dentista no BAIRRO {bairro} em {cidade} — conhece o {empresa}?"
    )
    out = substituir_placeholders(
        texto,
        empresa="Atelier Bucal",
        especialidade="estética",
        cidade="São Paulo",
        estado="SP",
        bairro="Ipiranga",
    )
    assert out == (
        "Dentista no BAIRRO Ipiranga em São Paulo — conhece o Atelier Bucal?"
    )
    assert "{cidade}" not in out
    assert "{bairro}" not in out
    assert "{empresa}" not in out


# ── Avaliação ──


def test_avaliar_detalhado():
    eng = ScoringEngine()
    r = eng.avaliar_resposta(mock_citado_detalhado, MOCK_EMPRESA)
    assert r["citou"] is True
    assert r["nivel"] == "detalhado"
    assert r["pontuacao"] == 10


def test_avaliar_superficial():
    eng = ScoringEngine()
    r = eng.avaliar_resposta(mock_citado_superficial, MOCK_EMPRESA)
    assert r["citou"] is True
    assert r["nivel"] == "superficial"
    assert r["pontuacao"] == 6


def test_avaliar_vago():
    eng = ScoringEngine()
    r = eng.avaliar_resposta(mock_vago, MOCK_EMPRESA)
    assert r["citou"] is True
    assert r["nivel"] == "vago"
    assert r["pontuacao"] == 3


def test_avaliar_nao_citado():
    eng = ScoringEngine()
    r = eng.avaliar_resposta(mock_nao_citado, MOCK_EMPRESA)
    assert r["citou"] is False
    assert r["nivel"] == "nao_citado"
    assert r["pontuacao"] == 0


# ── Bloco 1 — Visibilidade nas IAs ──


def _resultado(
    ia: str,
    pid,
    citou: bool,
    resposta: str = "ok",
    texto: str = "pergunta",
) -> ResultadoIA:
    return ResultadoIA(
        ia_nome=ia,
        pergunta_id=pid,
        pergunta_texto=texto,
        resposta_completa=resposta,
        citou_empresa=citou,
        nivel_citacao=NivelCitacaoEnum.superficial if citou else NivelCitacaoEnum.nao_citado,
        pontuacao=6.0 if citou else 0.0,
        trecho_relevante="trecho" if citou else None,
    )


def test_bloco1_r3_e_r4_nota_2():
    """Caso da planilha: aparição em R3+R4 → menor nota = 2."""
    eng = ScoringEngine()
    pid_r3, pid_r4 = uuid4(), uuid4()
    mapa = {pid_r3: "r3", pid_r4: "r4"}
    resultados = [
        _resultado("chatgpt", pid_r3, True),
        _resultado("chatgpt", pid_r4, True),
        _resultado("gemini", pid_r4, True),
        _resultado("claude", pid_r4, True),
        _resultado("perplexity", pid_r4, True),
    ]
    b1 = eng.calcular_bloco1_visibilidade(resultados, mapa)
    por = {n.ia_nome: n for n in b1.por_ia}
    assert por["chatgpt"].nota == 2.0
    assert sorted(por["chatgpt"].rodadas_com_aparicao) == ["r3", "r4"]
    assert por["gemini"].nota == 2.0
    assert por["claude"].nota == 2.0
    assert por["perplexity"].nota == 2.0
    assert b1.media == 2.0
    assert b1.interpretacao.value == "invisivel"


def test_bloco1_r1_nota_7():
    eng = ScoringEngine()
    pid = uuid4()
    b1 = eng.calcular_bloco1_visibilidade(
        [_resultado("chatgpt", pid, True)],
        {pid: "r1"},
        ias_ativas=["chatgpt"],
    )
    assert b1.por_ia[0].nota == 7.0
    assert b1.media == 7.0
    assert "buscas" in b1.interpretacao_label.lower() or b1.interpretacao.value == "buscas_especificas"


def test_bloco1_sem_aparicao_nota_0():
    eng = ScoringEngine()
    pid = uuid4()
    b1 = eng.calcular_bloco1_visibilidade(
        [_resultado("chatgpt", pid, False)],
        {pid: "r1"},
        ias_ativas=["chatgpt"],
    )
    assert b1.por_ia[0].nota == 0.0
    assert b1.media == 0.0


def test_bloco1_erro_tecnico_excluido_da_media():
    eng = ScoringEngine()
    pid = uuid4()
    resultados = [
        _resultado("chatgpt", pid, True),
        _resultado("gemini", pid, False, resposta="ERRO_TIMEOUT"),
    ]
    b1 = eng.calcular_bloco1_visibilidade(
        resultados, {pid: "r5"}, ias_ativas=["chatgpt", "gemini"]
    )
    por = {n.ia_nome: n for n in b1.por_ia}
    assert por["chatgpt"].nota == 9.0
    assert por["gemini"].disponivel is False
    assert b1.media == 9.0
    assert "gemini" in b1.ias_indisponiveis


def test_bloco1_media_igual_quatro_ias():
    eng = ScoringEngine()
    pids = {ia: uuid4() for ia in ("chatgpt", "gemini", "claude", "perplexity")}
    # notas: 7, 2, 0, 9 → média 4.5
    resultados = [
        _resultado("chatgpt", pids["chatgpt"], True),
        _resultado("gemini", pids["gemini"], True),
        _resultado("claude", pids["claude"], False),
        _resultado("perplexity", pids["perplexity"], True),
    ]
    mapa = {
        pids["chatgpt"]: "r1",
        pids["gemini"]: "r4",
        pids["claude"]: "r1",
        pids["perplexity"]: "r5",
    }
    b1 = eng.calcular_bloco1_visibilidade(resultados, mapa)
    assert b1.media == 4.5
    assert b1.ias_avaliadas == 4


def test_diagnostico_result_sem_bloco1_compativel():
    """Resultados antigos sem bloco1_visibilidade continuam válidos."""
    req = DiagnosticoRequest(
        empresa_nome="X",
        segmento=SegmentoEnum.odontologia,
        especialidade="geral",
        cidade="SP",
        estado="SP",
        perguntas_ids=[uuid4() for _ in range(5)],
    )
    r = DiagnosticoResult(
        request=req,
        resultados_ias=[],
        scores={},
        score_geral=1.8,
        status=StatusEnum.critico,
    )
    assert r.bloco1_visibilidade is None
    html = ReportGenerator().gerar_html(r)
    assert "Bloco 1 — Visibilidade" not in html
    assert "Diagnóstico Final" in html


def test_bloco1_nao_altera_score_geral():
    eng = ScoringEngine()
    seo = ScoreDimensao(nome="seo", peso=0.25, pontuacao_bruta=8.0, pontuacao_ponderada=2.0)
    llmo = ScoreDimensao(nome="llmo", peso=0.30, pontuacao_bruta=2.0, pontuacao_ponderada=0.6)
    aut = ScoreDimensao(nome="aut", peso=0.25, pontuacao_bruta=1.0, pontuacao_ponderada=0.25)
    cont = ScoreDimensao(nome="cont", peso=0.20, pontuacao_bruta=5.0, pontuacao_ponderada=1.0)
    score, status = eng.calcular_score_geral(seo, llmo, aut, cont)
    pid = uuid4()
    b1 = eng.calcular_bloco1_visibilidade(
        [_resultado("chatgpt", pid, True)],
        {pid: "r5"},
        ias_ativas=["chatgpt"],
    )
    # score_geral permanece 3.85 independentemente do Bloco 1
    assert abs(score - 3.85) < 0.01
    assert b1.media == 9.0
    assert status == StatusEnum.baixo


# ── Blocos manuais + SCORE TOTAL ──


def test_bloco_manual_ignora_vazios():
    eng = ScoringEngine()
    plan = eng.calcular_blocos_manuais_e_total(
        bloco1_media=None,
        notas={"b2_faq": 0},  # blog e cidade vazios
    )
    b2 = next(b for b in plan.blocos_manuais if b.id == "bloco2")
    assert b2.media == 0.0
    assert plan.score_total.media == 0.0


def test_score_total_caso_planilha_atelier():
    """Replica C36 ≈ 2.8194 com Bloco1=2 e notas da planilha Atelier Bucal."""
    eng = ScoringEngine()
    notas = {
        "b2_faq": 0,
        # b2_blog e b2_cidade vazios → Bloco2 média = 0
        "b3_doctoralia": 0,
        "b3_boaconsulta": 0,
        "b3_mencoes": 0,
        "b3_linkedin": 5,
        "b4_localbusiness": 0,
        "b4_tipo_especifico": 0,
        "b4_faqpage": 0,
        "b5_perfil": 7,
        "b5_avaliacoes": 9,
        "b5_posts": 3,
        "b6_nap": 10,
        "b6_respostas": 9,
        "b6_instagram": 3,
    }
    plan = eng.calcular_blocos_manuais_e_total(bloco1_media=2.0, notas=notas)
    assert plan.score_total is not None
    # (2 + 0 + 1.25 + 0 + 6.333... + 7.333...) / 6 ≈ 2.8194 → 2.82
    assert abs(plan.score_total.media - 2.82) < 0.02
    assert plan.score_total.interpretacao.value == "invisivel"
    assert "bloco1" in plan.score_total.blocos_no_calculo
    assert len(plan.score_total.blocos_no_calculo) == 6


def test_bloco_sem_notas_nao_entra_no_total():
    eng = ScoringEngine()
    plan = eng.calcular_blocos_manuais_e_total(
        bloco1_media=2.0,
        notas={"b5_perfil": 7, "b5_avaliacoes": 9, "b5_posts": 3},
    )
    # Só bloco1 e bloco5
    assert set(plan.score_total.blocos_no_calculo) == {"bloco1", "bloco5"}
    # (2 + 6.333...) / 2 ≈ 4.17
    assert abs(plan.score_total.media - 4.17) < 0.02


def test_score_geral_inalterado_apos_planilha():
    eng = ScoringEngine()
    seo = ScoreDimensao(nome="seo", peso=0.25, pontuacao_bruta=8.0, pontuacao_ponderada=2.0)
    llmo = ScoreDimensao(nome="llmo", peso=0.30, pontuacao_bruta=2.0, pontuacao_ponderada=0.6)
    aut = ScoreDimensao(nome="aut", peso=0.25, pontuacao_bruta=1.0, pontuacao_ponderada=0.25)
    cont = ScoreDimensao(nome="cont", peso=0.20, pontuacao_bruta=5.0, pontuacao_ponderada=1.0)
    score, _ = eng.calcular_score_geral(seo, llmo, aut, cont)
    plan = eng.calcular_blocos_manuais_e_total(2.0, {"b2_faq": 10, "b2_blog": 10, "b2_cidade": 10})
    assert abs(score - 3.85) < 0.01
    assert plan.score_total.media is not None
    assert plan.score_total.media != score


def test_endpoint_blocos_manuais_persiste(client, monkeypatch, tmp_path):
    from main import app
    import api.routes as routes

    # Monta um job concluído mínimo em memória
    job_id = uuid4()
    req = DiagnosticoRequest(
        empresa_nome="Atelier Bucal",
        segmento=SegmentoEnum.odontologia,
        especialidade="odontologia geral",
        cidade="São Paulo",
        estado="SP",
        perguntas_ids=[uuid4() for _ in range(5)],
    )
    from models.schemas import Bloco1Visibilidade

    resultado = DiagnosticoResult(
        request=req,
        resultados_ias=[],
        scores={},
        score_geral=1.8,
        status=StatusEnum.critico,
        bloco1_visibilidade=Bloco1Visibilidade(
            media=2.0,
            interpretacao_label="Invisível nas IAs",
            ias_avaliadas=3,
        ),
        diagnostico_planilha=ScoringEngine().calcular_blocos_manuais_e_total(2.0, {}),
    )
    routes.job_store.salvar(
        job_id,
        {
            "status": "concluido",
            "progresso": 100,
            "resultado": resultado.model_dump(mode="json"),
            "favorito": False,
        },
    )

    auth = ("catia", os.environ.get("PAINEL_SENHA", "teste12345678"))
    r = client.put(
        f"/api/diagnostico/{job_id}/blocos-manuais",
        json={"notas": {"b2_faq": 0, "b5_perfil": 7, "b5_avaliacoes": 9, "b5_posts": 3}},
        auth=auth,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score_geral"] == 1.8  # inalterado
    assert data["diagnostico_planilha"]["notas_salvas"]["b2_faq"] == 0
    assert data["diagnostico_planilha"]["score_total"]["media"] is not None

    # Reidrata
    job = routes.job_store.get(job_id)
    assert job["resultado"]["diagnostico_planilha"]["notas_salvas"]["b5_perfil"] == 7


# ── Scoring ──


def test_pesos_somam_1():
    assert abs(sum(ScoringEngine.PESOS_DIMENSAO.values()) - 1.0) < 1e-9


def test_score_geral_calculo():
    eng = ScoringEngine()
    seo = ScoreDimensao(nome="seo", peso=0.25, pontuacao_bruta=8.0, pontuacao_ponderada=2.0)
    llmo = ScoreDimensao(nome="llmo", peso=0.30, pontuacao_bruta=2.0, pontuacao_ponderada=0.6)
    aut = ScoreDimensao(nome="aut", peso=0.25, pontuacao_bruta=1.0, pontuacao_ponderada=0.25)
    cont = ScoreDimensao(nome="cont", peso=0.20, pontuacao_bruta=5.0, pontuacao_ponderada=1.0)
    # Override ponderadas to match test formula
    seo.pontuacao_ponderada = 8.0 * 0.25
    llmo.pontuacao_ponderada = 2.0 * 0.30
    aut.pontuacao_ponderada = 1.0 * 0.25
    cont.pontuacao_ponderada = 5.0 * 0.20
    score, status = eng.calcular_score_geral(seo, llmo, aut, cont)
    # 8×0.25 + 2×0.30 + 1×0.25 + 5×0.20 = 2.0+0.6+0.25+1.0 = 3.85
    assert abs(score - 3.85) < 0.01
    assert status == StatusEnum.baixo


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (1.5, StatusEnum.critico),
        (3.0, StatusEnum.baixo),
        (5.0, StatusEnum.medio),
        (7.0, StatusEnum.bom),
        (8.5, StatusEnum.excelente),
    ],
)
def test_status_limites(valor, esperado):
    eng = ScoringEngine()
    s = ScoreDimensao(nome="x", peso=1.0, pontuacao_bruta=valor, pontuacao_ponderada=valor)
    # Usar uma dimensão com peso total equivalente via pontuacao_ponderada
    zero = ScoreDimensao(nome="z", peso=0, pontuacao_bruta=0, pontuacao_ponderada=0)
    # score_geral = soma ponderadas; setamos só uma
    s.pontuacao_ponderada = valor
    score, status = eng.calcular_score_geral(s, zero, zero, zero)
    assert status == esperado


# ── Relatório ──


def test_report_contem_empresa(resultado_critico):
    html = ReportGenerator().gerar_html(resultado_critico)
    assert MOCK_EMPRESA in html or resultado_critico.request.empresa_nome in html


def test_report_contem_diagnostico_final(resultado_bom):
    html = ReportGenerator().gerar_html(resultado_bom)
    assert "Diagnóstico Final" in html


def test_report_contem_nota_geral(resultado_bom):
    html = ReportGenerator().gerar_html(resultado_bom)
    assert "7.5" in html or "7,5" in html


def test_report_secao_final_e_ultima(resultado_bom):
    html = ReportGenerator().gerar_html(resultado_bom)
    assert html.index("Próximos Passos") < html.index("Diagnóstico Final")


# ── API ──


@pytest.fixture(scope="module")
def client():
    from main import app

    return TestClient(app)


def test_health_retorna_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "apis" in data
    for k in ("claude", "openai", "gemini", "perplexity"):
        assert k in data["apis"]


def test_health_nao_cobram_api(client, monkeypatch):
    chamado = {"n": 0}

    def boom(*a, **k):
        chamado["n"] += 1
        raise AssertionError("API não deveria ser chamada no health")

    monkeypatch.setattr("services.claude_service.ClaudeService.consultar", boom)
    monkeypatch.setattr("services.openai_service.OpenAIService.consultar", boom)
    r = client.get("/health")
    assert r.status_code == 200
    assert chamado["n"] == 0

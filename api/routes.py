"""Rotas FastAPI do sistema LLMO."""

from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from models.schemas import (
    BancoPerguntasQuery,
    BlocosManuaisUpdate,
    CategoriaEnum,
    DiagnosticoRequest,
    DiagnosticoResult,
    Pergunta,
    PerguntaCreate,
    PerguntaUpdate,
)
from scoring.engine import ScoringEngine
from scoring.gabarito_blocos import definicao_publica, ids_criterios_validos
from services.supabase_rest import supabase_configurado

logger = logging.getLogger(__name__)
security = HTTPBasic()
router = APIRouter()

# Preenchidos em main.py via app.state / dependências injetadas no módulo
banco = None
orchestrator = None
report_generator = None
job_store = None
servicos_ia: dict[str, Any] = {}
outputs_dir = "outputs"

# Rate limit simples: 10 diagnósticos/hora
_rate: dict[str, list[float]] = {}


def configurar_deps(
    banco_,
    orchestrator_,
    report_generator_,
    job_store_,
    servicos_ia_,
    outputs_dir_: str = "outputs",
) -> None:
    global banco, orchestrator, report_generator, job_store, servicos_ia, outputs_dir
    banco = banco_
    orchestrator = orchestrator_
    report_generator = report_generator_
    job_store = job_store_
    servicos_ia = servicos_ia_
    outputs_dir = outputs_dir_


def verificar_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    user = os.getenv("PAINEL_USUARIO", "catia")
    senha = os.getenv("PAINEL_SENHA", "")
    user_ok = secrets.compare_digest(credentials.username, user)
    senha_ok = secrets.compare_digest(credentials.password, senha or "")
    if not (user_ok and senha_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _checar_rate(ip: str) -> None:
    agora = time.time()
    janela = _rate.setdefault(ip, [])
    _rate[ip] = [t for t in janela if agora - t < 3600]
    if len(_rate[ip]) >= 10:
        raise HTTPException(429, "Limite de 10 diagnósticos/hora atingido")
    _rate[ip].append(agora)


# ───────── Perguntas ─────────


@router.get("/perguntas", response_model=list[Pergunta])
def listar_perguntas(
    segmento: str | None = None,
    especialidade: str | None = None,
    categoria: CategoriaEnum | None = None,
    apenas_ativas: bool = True,
    busca_texto: str | None = None,
    _: str = Depends(verificar_auth),
):
    query = BancoPerguntasQuery(
        segmento=segmento,
        especialidade=especialidade,
        categoria=categoria,
        apenas_ativas=apenas_ativas,
        busca_texto=busca_texto,
    )
    return banco.listar(query)


@router.get("/perguntas/segmentos")
def listar_segmentos(_: str = Depends(verificar_auth)):
    return banco.listar_segmentos_especialidades()


@router.get("/perguntas/sugestao", response_model=list[Pergunta])
def sugerir_perguntas(
    segmento: str,
    especialidade: str,
    limite: int = 10,
    _: str = Depends(verificar_auth),
):
    return banco.sugerir_para_diagnostico(segmento, especialidade, limite=limite)


@router.get("/perguntas/{id}", response_model=Pergunta)
def obter_pergunta(id: UUID, _: str = Depends(verificar_auth)):
    p = banco.buscar_por_id(id)
    if not p:
        raise HTTPException(404, "Pergunta não encontrada")
    return p


@router.post("/perguntas", response_model=Pergunta, status_code=201)
def criar_pergunta(body: PerguntaCreate, _: str = Depends(verificar_auth)):
    return banco.criar(
        texto=body.texto,
        segmento=body.segmento,
        categoria=body.categoria.value,
        especialidade=body.especialidade,
        rodada=body.rodada.value if body.rodada else None,
    )


@router.put("/perguntas/{id}", response_model=Pergunta)
def atualizar_pergunta(
    id: UUID, body: PerguntaUpdate, _: str = Depends(verificar_auth)
):
    try:
        dados = body.model_dump(exclude_unset=True)
        if "categoria" in dados and dados["categoria"] is not None:
            dados["categoria"] = (
                dados["categoria"].value
                if hasattr(dados["categoria"], "value")
                else dados["categoria"]
            )
        if "rodada" in dados and dados["rodada"] is not None:
            dados["rodada"] = (
                dados["rodada"].value
                if hasattr(dados["rodada"], "value")
                else dados["rodada"]
            )
        return banco.atualizar(id, dados)
    except KeyError:
        raise HTTPException(404, "Pergunta não encontrada") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/perguntas/{id}", status_code=204)
def desativar_pergunta(id: UUID, _: str = Depends(verificar_auth)):
    try:
        banco.desativar(id)
    except KeyError:
        raise HTTPException(404, "Pergunta não encontrada") from None
    return Response(status_code=204)


@router.delete("/perguntas/{id}/permanente", status_code=204)
def deletar_pergunta(id: UUID, _: str = Depends(verificar_auth)):
    try:
        banco.deletar(id)
    except KeyError:
        raise HTTPException(404, "Pergunta não encontrada") from None
    return Response(status_code=204)


# ───────── Diagnóstico ─────────


@router.post("/diagnostico/estimar")
async def estimar_diagnostico(
    body: DiagnosticoRequest, _: str = Depends(verificar_auth)
):
    est = await orchestrator.estimar_custo(body)
    return {
        "custo_usd": est["total_usd"],
        "custo_brl": est["total_brl"],
        "tempo_estimado_seg": est["tempo_estimado_seg"],
        "num_perguntas": len(body.perguntas_ids),
        "num_ias": len(body.ias_ativas),
        "total_chamadas_api": est["total_chamadas_api"],
        "por_ia": est["por_ia"],
    }


async def _rodar_job(job_id: UUID, request: DiagnosticoRequest) -> None:
    def on_progress(info: dict) -> None:
        atual = job_store.get(job_id) or {}
        atual.update(
            {
                "status": "rodando",
                "progresso": info.get("pct", 0),
                "etapa": info.get("etapa", ""),
            }
        )
        job_store.salvar(job_id, atual)

    try:
        job_store.salvar(
            job_id,
            {
                "status": "rodando",
                "progresso": 0,
                "etapa": "iniciando",
                "resultado": None,
                "erro": None,
                "favorito": False,
                "request": request.model_dump(mode="json"),
            },
        )
        resultado = await orchestrator.rodar_diagnostico(request, on_progress)
        # salva HTML
        try:
            report_generator.salvar_html(resultado, pasta=outputs_dir)
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao salvar HTML: %s", e)

        job_store.salvar(
            job_id,
            {
                "status": "concluido",
                "progresso": 100,
                "etapa": "concluído",
                "resultado": resultado.model_dump(mode="json"),
                "erro": None,
                "favorito": False,
                "request": request.model_dump(mode="json"),
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Job %s falhou", job_id)
        job_store.salvar(
            job_id,
            {
                "status": "erro",
                "progresso": 0,
                "etapa": "erro",
                "resultado": None,
                "erro": str(e),
                "favorito": False,
                "request": request.model_dump(mode="json"),
            },
        )


@router.post("/diagnostico/iniciar")
async def iniciar_diagnostico(
    body: DiagnosticoRequest,
    background: BackgroundTasks,
    request: Request,
    _: str = Depends(verificar_auth),
):
    _checar_rate(request.client.host if request.client else "local")
    for pid in body.perguntas_ids:
        if banco.buscar_por_id(pid) is None:
            raise HTTPException(400, f"Pergunta {pid} não encontrada no banco")

    job_id = uuid4()
    job_store.salvar(
        job_id,
        {
            "status": "iniciado",
            "progresso": 0,
            "etapa": "na fila",
            "resultado": None,
            "erro": None,
            "favorito": False,
            "request": body.model_dump(mode="json"),
        },
    )
    background.add_task(_rodar_job, job_id, body)
    return {"job_id": job_id, "status": "iniciado"}


@router.get("/diagnostico/{job_id}/status")
def status_diagnostico(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")
    return {
        "status": job.get("status"),
        "progresso": job.get("progresso", 0),
        "etapa_atual": job.get("etapa"),
        "erro": job.get("erro"),
    }


@router.get("/diagnostico/{job_id}/resultado")
def resultado_diagnostico(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")
    if job.get("status") == "rodando" or job.get("status") == "iniciado":
        raise HTTPException(status_code=425, detail="Diagnóstico ainda em andamento")
    if job.get("status") == "erro":
        raise HTTPException(500, job.get("erro") or "Erro no diagnóstico")
    return job.get("resultado")


@router.get("/diagnostico/gabarito-blocos")
def gabarito_blocos_manuais(
    segmento: str | None = None,
    _: str = Depends(verificar_auth),
):
    """Definição dos critérios dos blocos 2–6 para a UI (filtrável por segmento)."""
    return {"blocos": definicao_publica(segmento)}


@router.put("/diagnostico/{job_id}/blocos-manuais")
def atualizar_blocos_manuais(
    job_id: UUID,
    body: BlocosManuaisUpdate,
    _: str = Depends(verificar_auth),
):
    """
    Salva notas manuais dos blocos 2–6, recalcula médias e SCORE TOTAL.
    Não altera score_geral.
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")
    if job.get("status") != "concluido" or not job.get("resultado"):
        raise HTTPException(400, "Diagnóstico ainda não concluído")

    resultado = DiagnosticoResult.model_validate(job["resultado"])
    segmento = (
        resultado.request.segmento.value
        if hasattr(resultado.request.segmento, "value")
        else str(resultado.request.segmento)
    )
    validos = ids_criterios_validos(segmento)
    desconhecidos = set(body.notas.keys()) - validos
    if desconhecidos:
        raise HTTPException(
            400, f"Critérios desconhecidos: {', '.join(sorted(desconhecidos))}"
        )

    bloco1_media = (
        resultado.bloco1_visibilidade.media
        if resultado.bloco1_visibilidade
        else None
    )

    # Merge com notas já salvas (permite update parcial)
    notas_atuais: dict[str, float | None] = {}
    if resultado.diagnostico_planilha and resultado.diagnostico_planilha.notas_salvas:
        notas_atuais = dict(resultado.diagnostico_planilha.notas_salvas)
    for cid, nota in body.notas.items():
        if nota is None:
            notas_atuais.pop(cid, None)
        else:
            notas_atuais[cid] = nota

    scoring = ScoringEngine()
    planilha = scoring.calcular_blocos_manuais_e_total(
        bloco1_media, notas_atuais, segmento=segmento
    )
    resultado.diagnostico_planilha = planilha

    job["resultado"] = resultado.model_dump(mode="json")
    job_store.salvar(job_id, job)

    # Regenera relatório HTML se possível
    try:
        if report_generator:
            report_generator.salvar_html(resultado)
    except Exception:  # noqa: BLE001
        logger.warning("Falha ao regenerar relatório após blocos manuais", exc_info=True)

    return resultado


@router.get("/diagnostico/{job_id}/relatorio")
def relatorio_html(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job or not job.get("resultado"):
        raise HTTPException(404, "Resultado não disponível")
    resultado = DiagnosticoResult.model_validate(job["resultado"])
    html = report_generator.gerar_html(resultado)
    return HTMLResponse(content=html)


@router.get("/diagnostico/{job_id}/relatorio/download")
def baixar_relatorio(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job or not job.get("resultado"):
        raise HTTPException(404, "Resultado não disponível")
    resultado = DiagnosticoResult.model_validate(job["resultado"])
    html = report_generator.gerar_html(resultado)
    nome = report_generator.gerar_nome_arquivo(resultado)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ───────── Histórico ─────────


@router.get("/historico")
def listar_historico(
    segmento: str | None = None,
    cidade: str | None = None,
    limite: int = 20,
    pagina: int = 1,
    favoritos: bool = False,
    _: str = Depends(verificar_auth),
):
    items = []
    for job in job_store.listar():
        if job.get("status") != "concluido" or not job.get("resultado"):
            continue
        if favoritos and not job.get("favorito"):
            continue
        res = job["resultado"]
        req = res.get("request", {})
        if segmento and req.get("segmento") != segmento:
            continue
        if cidade and req.get("cidade", "").lower() != cidade.lower():
            continue
        items.append(
            {
                "job_id": job.get("job_id"),
                "empresa_nome": req.get("empresa_nome"),
                "especialidade": req.get("especialidade"),
                "segmento": req.get("segmento"),
                "cidade": req.get("cidade"),
                "score_geral": res.get("score_geral"),
                "status": res.get("status"),
                "created_at": res.get("created_at"),
                "favorito": job.get("favorito", False),
            }
        )
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    inicio = (pagina - 1) * limite
    return {
        "total": len(items),
        "pagina": pagina,
        "itens": items[inicio : inicio + limite],
    }


@router.get("/historico/{job_id}")
def historico_detalhe(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job or not job.get("resultado"):
        raise HTTPException(404, "Não encontrado")
    return job["resultado"]


@router.post("/historico/{job_id}/fav")
def toggle_favorito(job_id: UUID, _: str = Depends(verificar_auth)):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Não encontrado")
    job["favorito"] = not job.get("favorito", False)
    job_store.salvar(job_id, job)
    return {"favorito": job["favorito"]}


@router.delete("/historico/{job_id}", status_code=204)
def remover_historico(job_id: UUID, _: str = Depends(verificar_auth)):
    if not job_store.delete(job_id):
        raise HTTPException(404, "Não encontrado")
    return Response(status_code=204)


# ───────── Sistema ─────────


@router.get("/health")
def health():
    """Health barato — sem chamadas a APIs de IA."""
    apis = {
        "claude": "configurado" if os.getenv("ANTHROPIC_API_KEY") else "ausente",
        "openai": "configurado" if os.getenv("OPENAI_API_KEY") else "ausente",
        "gemini": "configurado" if os.getenv("GOOGLE_API_KEY") else "ausente",
        "perplexity": "configurado" if os.getenv("PERPLEXITY_API_KEY") else "ausente",
    }
    total = len(banco._perguntas) if banco else 0
    ativas = len([p for p in banco._perguntas if p.ativa]) if banco else 0
    jobs_ok = job_store.ok() if job_store else False
    degradado = any(v == "ausente" for v in apis.values()) or not jobs_ok
    return {
        "status": "degradado" if degradado else "ok",
        "version": "2.2.0",
        "apis": apis,
        "banco_perguntas": {"total": total, "ativas": ativas},
        "jobs_store": "ok" if jobs_ok else "erro",
        "persistencia": "supabase" if supabase_configurado() else "disco",
        "vercel": bool(os.getenv("VERCEL")),
    }


@router.post("/sistema/testar-conexoes")
async def testar_conexoes(_: str = Depends(verificar_auth)):
    resultados = {}
    detalhes = {}
    for nome, svc in servicos_ia.items():
        try:
            if not getattr(svc, "api_key", None):
                resultados[nome] = "erro"
                detalhes[nome] = "chave ausente"
                continue
            if svc.__class__.__name__ == "OpenAIService":
                resp = await svc.consultar("Responda apenas: ok", usar_busca=False)
            else:
                resp = await svc.consultar("Responda apenas: ok")
            if resp.startswith("ERRO_"):
                resultados[nome] = "erro"
                detalhes[nome] = resp
            else:
                resultados[nome] = "ok"
                detalhes[nome] = "ok"
        except Exception as e:  # noqa: BLE001
            resultados[nome] = "erro"
            detalhes[nome] = str(e)
    return {**resultados, "detalhes": detalhes}

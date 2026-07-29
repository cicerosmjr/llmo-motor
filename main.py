"""Entry point FastAPI — Sistema LLMO Vértice Carioca."""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import routes
from prompts.banco import BancoPerguntas
from report.generator import ReportGenerator
from services.claude_service import ClaudeService
from services.gemini_service import GeminiService
from services.job_store import JobStore
from services.openai_service import OpenAIService
from services.orchestrator import LLMOOrchestrator
from services.perplexity_service import PerplexityService
from services.site_auditor import SiteAuditor
from services.supabase_rest import supabase_configurado

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("llmo")


def _garantir_dir(caminho: Path) -> Path | None:
    """Cria diretório se o FS permitir; na Vercel (read-only) retorna None."""
    try:
        caminho.mkdir(parents=True, exist_ok=True)
        return caminho
    except OSError as e:
        logger.warning("Diretório %s indisponível (%s)", caminho, e)
        return None


def _dir_outputs() -> str:
    """outputs/ local, ou /tmp/llmo-outputs em FS read-only."""
    if _garantir_dir(Path("outputs")):
        return "outputs"
    tmp = Path(tempfile.gettempdir()) / "llmo-outputs"
    _garantir_dir(tmp)
    return str(tmp)


_usa_supabase = supabase_configurado()
if _usa_supabase:
    logger.info("Persistência: Supabase")
    job_store = JobStore(usar_supabase=True)
else:
    jobs_dir = _garantir_dir(Path("data/jobs"))
    if jobs_dir is None:
        raise RuntimeError(
            "Filesystem read-only e Supabase não configurado. "
            "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY "
            "(veja sql/supabase_schema.sql e DEPLOY.md)."
        )
    job_store = JobStore(jobs_dir)

banco = BancoPerguntas()
_outputs = _dir_outputs()

claude = ClaudeService(os.getenv("ANTHROPIC_API_KEY", ""))
openai_svc = OpenAIService(os.getenv("OPENAI_API_KEY", ""))
gemini = GeminiService(os.getenv("GOOGLE_API_KEY", ""))
perplexity = PerplexityService(os.getenv("PERPLEXITY_API_KEY", ""))
auditor = SiteAuditor()
report_gen = ReportGenerator()
orchestrator = LLMOOrchestrator(
    claude=claude,
    openai=openai_svc,
    gemini=gemini,
    perplexity=perplexity,
    banco=banco,
    auditor=auditor,
)

routes.configurar_deps(
    banco_=banco,
    orchestrator_=orchestrator,
    report_generator_=report_gen,
    job_store_=job_store,
    servicos_ia_={
        "claude": claude,
        "openai": openai_svc,
        "chatgpt": openai_svc,
        "gemini": gemini,
        "perplexity": perplexity,
    },
    outputs_dir_=_outputs,
)

app = FastAPI(title="LLMO Vértice Carioca", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    dur = (time.perf_counter() - inicio) * 1000
    logger.info("%s %s → %s (%.1fms)", request.method, request.url.path, response.status_code, dur)
    return response


app.include_router(routes.router, prefix="/api")
# Health também na raiz (Railway healthcheck / Vercel)
app.add_api_route("/health", routes.health, methods=["GET"])

static_dir = Path("static")
if not static_dir.is_dir():
    raise RuntimeError("Pasta static/ ausente no deploy")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def painel():
    return FileResponse("static/painel.html")

# PROMPTS PARA O CURSOR — Sistema LLMO Vértice Carioca
# Versão 2.1 — Foco em empresas + Banco de perguntas selecionável
# Adaptado para uso no Cursor (chat lateral + editor)
# Changelog 2.1: .cursor/rules; pesos de IA esclarecidos; scraper SEO/LLMO;
#   modelos atualizados; jobs persistentes em disco; health sem custo de API

---

## COMO USAR ESTES PROMPTS NO CURSOR

```
O Cursor funciona diferente do Claude Code:
- Você cria os arquivos manualmente (Ctrl+N) ou pede via chat
- O chat lateral (Ctrl+L) enxerga os arquivos que você deixar ABERTOS
- Para dar contexto ao Cursor, ABRA os arquivos relevantes antes de perguntar
- O Cursor autocompleta enquanto você digita (Tab para aceitar)
- Use @ para referenciar arquivos no chat: @models/schemas.py
- Memória permanente: `.cursor/rules/llmo-vertice.mdc` (não use `.cursorrules`)

FLUXO BÁSICO POR MÓDULO:
1. Crie a pasta/arquivo vazio no explorador do Cursor
2. Abra o arquivo (ele fica visível no chat)
3. Cole o prompt correspondente no chat lateral (Ctrl+L)
4. Revise e aceite o código gerado
5. Salve e teste no terminal integrado (Ctrl+`)
6. Só então avance para o próximo prompt
```

---

## REGRAS DO CURSOR — `.cursor/rules/` (crie na raiz do projeto)

> **Não use mais `.cursorrules` na raiz** (formato legado).
> Crie a pasta `.cursor/rules/` e o arquivo `llmo-vertice.mdc`.
> O Cursor carrega regras dessa pasta em TODA sessão — é a memória
> permanente do projeto. Cole o conteúdo abaixo em `.cursor/rules/llmo-vertice.mdc`:

```
---
description: Sistema LLMO — Vértice Carioca (convenções e domínio)
alwaysApply: true
---

# Sistema LLMO — Vértice Carioca
# Agência de marketing digital do Rio de Janeiro

## Sobre o projeto
Sistema de pesquisa LLMO (Large Language Model Optimization) para medir
a visibilidade de EMPRESAS nas IAs (ChatGPT, Gemini, Perplexity, Claude).
O cliente da Vértice é sempre uma EMPRESA — clínica médica, escritório
de advocacia, clínica de psicologia. Nunca profissional autônomo isolado.

## Stack
- Python 3.11 + FastAPI
- Deploy: Railway
- IAs: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Perplexity
- Armazenamento:
  - JSON em disco: banco de perguntas (`data/perguntas.json`)
  - JSON em disco: jobs/histórico (`data/jobs/`) — sobrevive a restart
  - Dict em memória: cache de progresso do job ativo (espelhado no disco)
- Painel: HTML/CSS/JS puro em /static/painel.html
- Auditor técnico: `services/site_auditor.py` (crawl do site_url para SEO/LLMO)

## Segmentos atendidos
- medicina (CFM Resolução 2.336/23)
- advocacia (OAB Provimento 205/2021)
- psicologia (CFP)
- outro

## Sistema de pontuação
Dimensões e pesos:
- seo_tecnico: 25%
- llmo_schema: 30%
- autoridade_citacao: 25%
- conteudo: 20%

Escala de citação:
- detalhado → 10 pts
- superficial → 6 pts
- vago → 3 pts
- nao_citado → 0 pts

Pesos por IA (para score de autoridade) — refletir share de uso no BR:
- chatgpt: 40%   ← maior peso (mais usado pelos clientes finais)
- gemini: 25%
- perplexity: 20%  ← peso menor no score, mas sinal diagnóstico forte
  (busca em tempo real; ausência = site fraco na web indexada HOJE)
- claude: 15%

Status por faixa de score:
- 0.0–2.9 → critico
- 3.0–4.9 → baixo
- 5.0–6.9 → medio
- 7.0–8.4 → bom
- 8.5–10  → excelente

## Modelos de IA (atualizar se a API mudar)
- Claude:     claude-sonnet-5
- ChatGPT:    gpt-4o-mini
- Gemini:     gemini-2.5-flash
- Perplexity: sonar

## Paleta visual
- Navy:    #0d1b2a
- Gold:    #c9a84c
- Cream:   #f5f0e8
- Danger:  #e05c4b
- Amber:   #e0a030
- Success: #4caf7d

## Convenções de código
- Tipagem completa com Pydantic v2
- async/await em todos os serviços de IA e no auditor de site
- Logging estruturado em cada chamada de API
- Tratamento de erro com retry em todos os serviços
- Comentários em português (projeto brasileiro)
- GET /health NÃO chama APIs de IA (só valida env + arquivos locais)
```

---

## CONTEXTO PARA COLAR NO CHAT (quando necessário)

> Use este bloco apenas se o Cursor parecer ter perdido o contexto
> do projeto. Normalmente as regras em `.cursor/rules/` são suficientes.

```
Contexto adicional para esta sessão:

O sistema LLMO da Vértice tem um BANCO DE PERGUNTAS central:
- Perguntas ficam salvas em /data/perguntas.json
- Cada pergunta tem placeholders: {empresa}, {especialidade}, {cidade}, {estado}
- Antes de cada diagnóstico, o usuário SELECIONA quais perguntas usar (5–20)
- O sistema substitui os placeholders com dados reais da empresa
- Depois envia as perguntas selecionadas a todas as IAs em paralelo

O relatório final termina com uma seção "Diagnóstico Final" que exibe:
- Nota geral de 0 a 10 (ex: 3.7/10)
- Label: CRÍTICO / BAIXO / MÉDIO / BOM / EXCELENTE
- Parágrafo de interpretação dinâmico por faixa de score
```

---

## PROMPT 1 — Estrutura do projeto

> **Antes de usar:** Abra o Cursor em uma pasta vazia.
> Cole no chat lateral (Ctrl+L):

```
Crie a estrutura completa de pastas e arquivos para o sistema LLMO
da Vértice Carioca. Use as convenções de @.cursor/rules/llmo-vertice.mdc
(ou as regras do projeto, se já existirem).

Entregue o conteúdo de cada arquivo abaixo:

1. requirements.txt
   Inclua: fastapi, uvicorn, pydantic, anthropic, openai,
   google-generativeai, httpx, beautifulsoup4, lxml, python-dotenv,
   pytest, pytest-asyncio

2. .env.example
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=
   GOOGLE_API_KEY=
   PERPLEXITY_API_KEY=
   PAINEL_USUARIO=catia
   PAINEL_SENHA=

3. railway.toml
   Configurado para deploy com Dockerfile, healthcheck em /health,
   restart on failure, sleep desabilitado.

4. .gitignore
   .env, __pycache__, *.pyc, outputs/, data/perguntas.json, data/jobs/

5. README.md
   Setup local em 5 passos:
   a) clonar repo
   b) criar venv e instalar requirements.txt
   c) copiar .env.example para .env e preencher as chaves
   d) python -c "from data.seed import inicializar" para criar o banco
   e) uvicorn main:app --reload e abrir localhost:8000

Mostre também a árvore de diretórios comentada que devo criar manualmente:
/api, /services, /prompts, /scoring, /report, /models, /data, /data/jobs,
/static, /tests, /.cursor/rules
```

---

## PROMPT 2 — Modelos de dados (Pydantic)

> **Antes de usar:**
> 1. Crie o arquivo `/models/schemas.py` (vazio)
> 2. Abra-o no editor
> 3. Cole no chat:

```
Escreva o conteúdo completo de /models/schemas.py com todos os modelos
Pydantic v2 do sistema LLMO. O arquivo está aberto no editor.

Modelos necessários:

1. CategoriaEnum
   Valores: reconhecimento, recomendacao, reputacao, servicos,
            localizacao, generica

2. SegmentoEnum
   Valores: medicina, advocacia, psicologia, outro

3. NivelCitacaoEnum
   Valores: detalhado, superficial, vago, nao_citado

4. StatusEnum
   Valores: critico, baixo, medio, bom, excelente

5. Pergunta
   id: UUID (default_factory=uuid4)
   texto: str — template com {empresa}, {especialidade}, {cidade}, {estado}
   segmento: str
   especialidade: str | None = None
   categoria: CategoriaEnum
   ativa: bool = True
   criada_em: datetime (default_factory=datetime.utcnow)
   criada_por: str = "vertice"

6. BancoPerguntasQuery (BaseModel)
   segmento: str | None = None
   especialidade: str | None = None
   categoria: CategoriaEnum | None = None
   apenas_ativas: bool = True
   busca_texto: str | None = None

7. DiagnosticoRequest
   empresa_nome: str
   empresa_razao_social: str | None = None
   site_url: str | None = None  — validator: deve ser URL válida se informada
   segmento: SegmentoEnum
   especialidade: str
   cidade: str
   estado: str = "RJ"
   perguntas_ids: list[UUID]  — validator: mínimo 5, máximo 20 itens
   ias_ativas: list[str] = ["claude", "chatgpt", "gemini", "perplexity"]

8. ResultadoIA
   ia_nome: str
   pergunta_id: UUID
   pergunta_texto: str
   resposta_completa: str
   citou_empresa: bool
   nivel_citacao: NivelCitacaoEnum
   pontuacao: float  — validator: entre 0 e 10
   trecho_relevante: str | None = None
   concorrentes_citados: list[str] = []

9. ScoreDimensao
   nome: str
   peso: float
   pontuacao_bruta: float
   pontuacao_ponderada: float
   detalhes: dict = {}

10. DiagnosticoResult
    id: UUID (default_factory=uuid4)
    created_at: datetime (default_factory=datetime.utcnow)
    request: DiagnosticoRequest
    resultados_ias: list[ResultadoIA]
    scores: dict[str, ScoreDimensao]
    score_geral: float
    status: StatusEnum
    concorrentes_mais_citados: list[dict] = []
    plano_acao: list[dict] = []
    resumo_executivo: str = ""

11. EmpresaCliente
    id: UUID (default_factory=uuid4)
    empresa_nome: str
    segmento: str
    especialidade: str
    site_url: str | None = None
    cidade: str
    estado: str
    diagnosticos: list[UUID] = []
    created_at: datetime (default_factory=datetime.utcnow)
    ultima_atualizacao: datetime (default_factory=datetime.utcnow)

Inclua todos os imports necessários no topo do arquivo.
```

---

## PROMPT 3 — Banco de perguntas

> **Antes de usar:**
> 1. Crie os arquivos vazios: `/prompts/banco.py`, `/prompts/substituidor.py`
> 2. Crie a pasta `/data/` com um arquivo `__init__.py` vazio
> 3. Abra `/prompts/banco.py` no editor
> 4. Cole no chat:

```
Escreva o conteúdo completo de /prompts/banco.py.
O arquivo @models/schemas.py já existe com os modelos Pydantic.

Implemente a classe BancoPerguntas:

class BancoPerguntas:
    CAMINHO_SEED = "data/perguntas_seed.json"
    CAMINHO_BANCO = "data/perguntas.json"

    def __init__(self):
        self._perguntas: list[Pergunta] = []
        self.carregar()

    def carregar(self) -> None
        # Se data/perguntas.json existir, carrega dele
        # Se não existir, copia do seed e salva

    def salvar(self) -> None
        # Serializa self._perguntas para data/perguntas.json

    def listar(self, query: BancoPerguntasQuery) -> list[Pergunta]
        # Filtra por segmento, especialidade, categoria, ativa, busca_texto
        # busca_texto: case-insensitive no campo texto da pergunta

    def buscar_por_id(self, id: UUID) -> Pergunta | None

    def criar(self, texto: str, segmento: str, categoria: str,
              especialidade: str | None = None) -> Pergunta
        # Cria Pergunta com UUID novo, salva e retorna

    def atualizar(self, id: UUID, dados: dict) -> Pergunta
        # Atualiza campos permitidos (texto, categoria, especialidade, ativa)

    def desativar(self, id: UUID) -> None
        # ativa = False, salva

    def deletar(self, id: UUID) -> None
        # Remove permanentemente, salva

    def sugerir_para_diagnostico(
        self,
        segmento: str,
        especialidade: str,
        incluir_genericas: bool = True,
        limite: int = 10
    ) -> list[Pergunta]:
        # Retorna seleção equilibrada:
        # Prioriza perguntas da especialidade específica; complementa com
        # perguntas do segmento geral se necessário.
        # Distribuição alvo:
        #   reconhecimento: 2, recomendacao: 2, reputacao: 2,
        #   servicos: 2, localizacao: 1, generica: 1
        # Se não houver perguntas suficientes de uma categoria, completa
        # com outras categorias até atingir o limite.

    def listar_segmentos_especialidades(self) -> dict:
        # Retorna {"medicina": ["cirurgia plástica", "dermatologia", ...],
        #          "advocacia": ["tributário", ...], ...}
        # Usado para popular dropdowns do painel
```

---

## PROMPT 3B — Seed de perguntas e substituidor

> **Antes de usar:**
> 1. Crie `/data/perguntas_seed.json` (vazio)
> 2. Crie `/prompts/substituidor.py` (vazio)
> 3. Abra os dois arquivos no editor
> 4. Cole no chat:

```
Escreva dois arquivos:

──────────────────────────────────────
ARQUIVO 1: /data/perguntas_seed.json
──────────────────────────────────────
JSON com lista de perguntas. Crie pelo menos 8 perguntas para cada
combinação de segmento/especialidade abaixo, usando os placeholders
{empresa}, {especialidade}, {cidade}, {estado}, {site_url}.

Combinações obrigatórias (segmento — especialidade):
- medicina — geral
- medicina — cirurgia plástica
- medicina — dermatologia
- medicina — odontologia
- medicina — psiquiatria
- advocacia — geral
- advocacia — direito tributário
- advocacia — direito imobiliário
- advocacia — planejamento patrimonial
- advocacia — direito trabalhista
- psicologia — geral
- psicologia — ansiedade e depressão
- psicologia — psicologia infantil
- geral — (qualquer segmento)

Para cada combinação, distribua as perguntas entre as 6 categorias:
reconhecimento, recomendacao, reputacao, servicos, localizacao, generica.

Formato de cada objeto no JSON:
{
  "texto": "...",
  "segmento": "medicina",
  "especialidade": "cirurgia plástica",
  "categoria": "recomendacao",
  "ativa": true,
  "criada_por": "vertice"
}
(sem campo "id" — é gerado no carregamento)

──────────────────────────────────────
ARQUIVO 2: /prompts/substituidor.py
──────────────────────────────────────
Implemente:

def substituir_placeholders(
    texto: str,
    empresa: str,
    especialidade: str,
    cidade: str,
    estado: str,
    site_url: str | None = None
) -> str:
    # Substitui {empresa}, {especialidade}, {cidade}, {estado}, {site_url}
    # Se site_url for None, substitui {site_url} pelo valor de empresa

def preparar_perguntas_diagnostico(
    perguntas: list[Pergunta],
    request: DiagnosticoRequest
) -> list[tuple[UUID, str]]:
    # Para cada pergunta, chama substituir_placeholders com dados do request
    # Retorna lista de (pergunta.id, texto_substituído)
```

---

## PROMPT 4 — Serviço Claude

> **Antes de usar:**
> 1. Crie `/services/claude_service.py` (vazio)
> 2. Abra-o no editor
> 3. Cole no chat:

```
Escreva o conteúdo completo de /services/claude_service.py.

Importe Pergunta e DiagnosticoRequest de @models/schemas.py.

class ClaudeService:
    MODELO = "claude-sonnet-5"
    MAX_TOKENS = 600
    # Sonnet 5: não enviar temperature/top_p customizados (API rejeita
    # sampling não-default). Use apenas max_tokens + messages.

    SYSTEM_PROMPT = """Você é um assistente útil respondendo perguntas de
    usuários brasileiros que buscam empresas e serviços profissionais nas
    áreas de saúde, direito e psicologia. Responda de forma natural e
    honesta com base no que você conhece. Se não souber ou não tiver certeza
    sobre uma empresa específica, diga isso claramente em vez de inventar."""

    def __init__(self, api_key: str):
        ...

    async def consultar(self, pergunta: str, contexto: str) -> str:
        # contexto: string curta descrevendo o tipo de empresa
        # Ex: "clínica de cirurgia plástica em Rio de Janeiro"
        # Retry com backoff: 1s → 2s → 4s em RateLimitError
        # Em APIError: log + retornar "ERRO_API: {msg}"
        # Em timeout >30s: retornar "ERRO_TIMEOUT"

    async def consultar_lote(
        self,
        perguntas: list[tuple[UUID, str]],
        contexto: str,
        delay: float = 0.5
    ) -> list[tuple[UUID, str]]:
        # Executa as perguntas em sequência com delay entre chamadas
        # Retorna lista de (pergunta_id, resposta)

    def estimar_custo(self, num_perguntas: int) -> dict:
        # Estimativa baseada em 600 tokens/pergunta
        # Preço input: $0.003/1K tokens, output: $0.015/1K tokens
        # Retorna: {"usd": float, "brl": float, "tokens_estimados": int}

Logging em cada chamada:
  logger.info(f"[Claude] '{pergunta[:50]}...' | tokens={n} | custo=${c:.4f}")
```

---

## PROMPT 5 — Serviço OpenAI

> **Antes de usar:** Crie e abra `/services/openai_service.py`. Cole no chat:

```
Escreva /services/openai_service.py.

Interface IDÊNTICA ao @services/claude_service.py, adaptada para OpenAI:
- SDK: openai
- Modelo: gpt-4o-mini
- Max tokens: 600, Temperature: 0.3
- MESMO system prompt do ClaudeService (copie exatamente)

class OpenAIService:
    def __init__(self, api_key: str)
    async def consultar(self, pergunta: str, contexto: str) -> str
    async def consultar_lote(self, perguntas, contexto, delay=0.5) -> list[tuple[UUID, str]]
    def estimar_custo(self, num_perguntas: int) -> dict

Mesmo tratamento de erro e logging. Logging deve marcar "[ChatGPT]".
```

---

## PROMPT 6 — Serviço Gemini

> **Antes de usar:** Crie e abra `/services/gemini_service.py`. Cole no chat:

```
Escreva /services/gemini_service.py.

Interface idêntica ao @services/claude_service.py, adaptada para Gemini:
- SDK: google-generativeai
- Modelo: gemini-2.5-flash
- Max tokens: 600, Temperature: 0.3
- MESMO system prompt dos outros serviços
- NOTA: antes de out/2026, avaliar upgrade para gemini-3.5-flash (2.5 retira)

ATENÇÃO: O SDK do Gemini é SÍNCRONO. Use asyncio.to_thread() em todas
as chamadas para não bloquear o event loop do FastAPI.

class GeminiService:
    def __init__(self, api_key: str)
    async def consultar(self, pergunta: str, contexto: str) -> str
    async def consultar_lote(self, perguntas, contexto, delay=0.5) -> list[tuple[UUID, str]]
    def estimar_custo(self, num_perguntas: int) -> dict

Logging deve marcar "[Gemini]".
```

---

## PROMPT 7 — Serviço Perplexity

> **Antes de usar:** Crie e abra `/services/perplexity_service.py`. Cole no chat:

```
Escreva /services/perplexity_service.py.

Perplexity usa a API compatível com OpenAI, com endpoint próprio:
- Base URL: https://api.perplexity.ai
- Modelo: sonar   (alternativa mais cara: sonar-pro)
- Max tokens: 600, Temperature: 0.3
- MESMO system prompt dos outros serviços

DIFERENCIAL CRÍTICO: Perplexity usa busca em TEMPO REAL.
Uma empresa não citada pela Perplexity está ausente da web indexada HOJE —
não apenas dos dados históricos de treinamento. Isso deve aparecer no log
e no plano de ação (prioridade URGENTE). NÃO confundir com peso no score:
no ScoringEngine, Perplexity tem peso 20% (ChatGPT tem 40%).

class PerplexityService:
    def __init__(self, api_key: str)
    async def consultar(self, pergunta: str, contexto: str) -> str
    async def consultar_lote(self, perguntas, contexto, delay=1.0) -> list[tuple[UUID, str]]
    def estimar_custo(self, num_perguntas: int) -> dict

Logging: "[Perplexity REAL-TIME] '{pergunta[:50]}...' | ..."
Use delay padrão de 1.0s (mais lento que os outros — respeitar rate limit).
```

---

## PROMPT 7B — Auditor técnico do site (SEO + LLMO)

> **Antes de usar:** Crie e abra `/services/site_auditor.py`. Cole no chat:
>
> **Por quê:** os scores `seo_tecnico`, `llmo_schema` e `conteudo` dependem de
> checks reais no site. Sem este serviço, o orquestrador não tem dados para
> pontuar essas dimensões.

```
Escreva /services/site_auditor.py.

Use httpx (async) + BeautifulSoup. Timeout total 15s por URL.

class SiteAuditor:
    USER_AGENT = "LLMO-Vertice/2.1 (+https://verticecarioca.com.br; auditor)"

    async def auditar(self, site_url: str | None) -> dict:
        """
        Se site_url for None ou inválida, retorna checks com todos False
        e meta={"motivo": "site_url_ausente"} — o scoring recebe 0 nessas dimensões.

        Fluxo:
        1. GET site_url (follow redirects, verify SSL)
        2. GET {origem}/robots.txt
        3. GET {origem}/sitemap.xml (ou URL apontada no robots)
        4. GET {origem}/llms.txt
        5. Parse HTML e montar dois dicts de checks booleanos

        Retorna:
        {
          "seo": {
            "ssl": bool,              # URL final começa com https
            "meta_description": bool,
            "canonical": bool,
            "viewport": bool,
            "sitemap": bool,          # sitemap.xml acessível (200)
            "robots": bool,           # robots.txt acessível (200)
            "open_graph": bool,       # ao menos og:title + og:description
            "h1": bool,               # existe exatamente 1+ h1
            "conteudo_html": bool,    # texto visível > 500 chars
          },
          "llmo": {
            "schema_ld": bool,           # script type=application/ld+json
            "faq_schema": bool,          # @type FAQPage no JSON-LD
            "local_business": bool,      # LocalBusiness / MedicalBusiness /
                                         # LegalService / ProfessionalService
            "llms_txt": bool,            # /llms.txt retornou 200
            "open_graph_completo": bool, # og:title, og:description, og:image, og:url
          },
          "conteudo": {
            "h1_presente": bool,
            "estrutura_semantica": bool,  # main/article/section ou headings h2+
            "conteudo_substancial": bool, # texto visível > 3000 chars
            "blog_ativo": bool,           # link/path com blog|artigos|noticias
          },
          "meta": {
            "url_final": str | None,
            "status_http": int | None,
            "erro": str | None,
            "tempo_ms": int
          }
        }

        Em erro de rede/timeout/SSL: preencher checks=False, meta.erro=msg,
        NÃO levantar exceção (o diagnóstico deve continuar só com citação nas IAs).
        """

Logging: logger.info(f"[SiteAuditor] {url} | status={s} | ssl={ssl} | schema={ld}")
```

---

## PROMPT 8 — Orquestrador

> **Antes de usar:**
> 1. Crie e abra `/services/orchestrator.py`
> 2. Certifique-se que os 4 serviços, o site_auditor e o substituidor estão salvos
> 3. Cole no chat:

```
Escreva /services/orchestrator.py.

Importe de @models/schemas.py, @services/claude_service.py,
@services/openai_service.py, @services/gemini_service.py,
@services/perplexity_service.py, @services/site_auditor.py,
@prompts/banco.py, @prompts/substituidor.py, @scoring/engine.py.

class LLMOOrchestrator:
    def __init__(self, claude, openai, gemini, perplexity, banco, auditor=None):
        self.servicos = {
            "claude": claude, "chatgpt": openai,
            "gemini": gemini, "perplexity": perplexity
        }
        self.banco = banco
        self.auditor = auditor or SiteAuditor()

    async def rodar_diagnostico(
        self,
        request: DiagnosticoRequest,
        progress_callback = None   # Callable[dict] | None
    ) -> DiagnosticoResult:
        """
        Fluxo completo:

        1. Buscar objetos Pergunta pelos IDs em request.perguntas_ids
           (lança ValueError se algum ID não existir no banco)

        2. Chamar preparar_perguntas_diagnostico() para substituir placeholders

        3. Montar contexto da empresa:
           "{empresa_nome} — {especialidade} em {cidade}, {estado}"

        4. Em paralelo com as IAs: await self.auditor.auditar(request.site_url)
           → checks_seo, checks_llmo, checks_conteudo
           progress_callback: {"etapa": "Auditoria do site", "pct": 10}

        5. Disparar asyncio.gather() com todos os serviços ativos em paralelo:
           tasks = [servico.consultar_lote(perguntas_prep, contexto)
                    for nome, servico in servicos_ativos.items()]
           resultados_brutos = await asyncio.gather(*tasks)

        6. Para cada resposta, chamar ScoringEngine.avaliar_resposta()
           e montar lista de ResultadoIA

        7. Emitir progress_callback a cada IA concluída:
           {"etapa": "ChatGPT concluído (10/10)", "pct": 50}

        8. Chamar ScoringEngine:
           - calcular_score_autoridade(resultados)
           - calcular_score_seo(checks["seo"])
           - calcular_score_llmo(checks["llmo"], resultados)
           - calcular_score_conteudo(checks["conteudo"])
           - calcular_score_geral(...)
           NUNCA passar dicts vazios/fictícios se o auditor rodou —
           use exatamente o retorno de SiteAuditor.auditar().

        9. Chamar _extrair_concorrentes() para identificar quem a IA
           cita no lugar da empresa

        10. Chamar _gerar_plano_acao() com base nos scores, gaps e checks

        11. Montar e retornar DiagnosticoResult completo
            (incluir checks no campo scores.*.detalhes quando fizer sentido)
        """

    def _extrair_concorrentes(
        self,
        resultados: list[ResultadoIA],
        empresa_nome: str
    ) -> list[dict]:
        """
        Varre o campo concorrentes_citados de cada ResultadoIA,
        agrega por nome e ordena por frequência.
        Retorna: [{"nome": str, "vezes_citado": int}, ...]
        Exclui variações do nome da própria empresa.
        """

    def _gerar_plano_acao(
        self,
        scores: dict,
        resultados: list[ResultadoIA],
        request: DiagnosticoRequest
    ) -> list[dict]:
        """
        Regras:

        URGENTE se score llmo_schema < 3:
          → "Implementar Schema JSON-LD LocalBusiness no site de {empresa}"
          → "Criar arquivo llms.txt na raiz do domínio"

        URGENTE se nenhuma IA citou (score autoridade == 0):
          → "Criar FAQ estruturado com FAQPage Schema (mínimo 8 perguntas)"
          → "Registrar e otimizar perfil no Google Meu Negócio"

        URGENTE se Perplexity não citou:
          → "Publicar perfil em diretórios especializados de {segmento}"

        30_DIAS se score seo_tecnico < 4:
          → "Adicionar meta description única em todas as páginas"
          → "Criar sitemap.xml e submeter ao Google Search Console"

        30_DIAS se score conteudo < 4:
          → "Publicar 4 artigos de blog sobre {especialidade} em 30 dias"

        30_DIAS se concorrentes encontrados:
          → "Analisar presença digital de: {nomes dos top 3 concorrentes}"

        CONTINUO (sempre):
          → "Monitoramento mensal de citação nas 4 IAs"
          → "Publicação quinzenal de conteúdo educativo sobre {especialidade}"

        Retorna lista ordenada: urgente primeiro, depois 30_dias, depois continuo.
        Formato: [{"prioridade": str, "acao": str}, ...]
        """

    async def estimar_custo(self, request: DiagnosticoRequest) -> dict:
        """
        Sem chamar APIs reais — cálculo matemático baseado em:
        num_perguntas × num_ias × custo_por_pergunta_por_ia
        Retorna: {
            "por_ia": {"claude": {...}, "chatgpt": {...}, ...},
            "total_usd": float,
            "total_brl": float,
            "tempo_estimado_seg": int,
            "total_chamadas_api": int
        }
        """
```

---

## PROMPT 9 — Engine de scoring

> **Antes de usar:** Crie e abra `/scoring/engine.py`. Cole no chat:

```
Escreva /scoring/engine.py.
Importe modelos de @models/schemas.py.

class ScoringEngine:

    PESOS_DIMENSAO = {
        "seo_tecnico":       0.25,
        "llmo_schema":       0.30,
        "autoridade_citacao":0.25,
        "conteudo":          0.20,
    }

    PESOS_IA = {
        "chatgpt":    0.40,  # maior peso — share de uso no Brasil
        "gemini":     0.25,
        "perplexity": 0.20,  # peso menor; sinal diagnóstico de web real-time
        "claude":     0.15,
    }

    PONTUACAO_CITACAO = {
        "detalhado":   10.0,
        "superficial":  6.0,
        "vago":         3.0,
        "nao_citado":   0.0,
    }

    def avaliar_resposta(self, resposta: str, empresa_nome: str) -> dict:
        """
        Detecta citação da empresa e classifica o nível.
        Busca case-insensitive. Considera variações (siglas, abreviações).

        Heurísticas de nível:
        - detalhado: nome + (endereço OU telefone OU serviço específico
                     OU ano de fundação OU especialista OU prêmio)
        - superficial: nome aparece claramente mas sem detalhes
        - vago: parte do nome ou nome ambíguo
        - nao_citado: nome não detectado

        Retorna:
        {
          "citou": bool,
          "nivel": str,
          "pontuacao": float,
          "trecho": str | None   # até 200 chars ao redor da citação
        }
        """

    def calcular_score_autoridade(
        self, resultados: list[ResultadoIA]
    ) -> ScoreDimensao:
        """
        Para cada IA: média das pontuações das perguntas respondidas.
        Score final: soma ponderada pelos PESOS_IA.
        
        detalhes = {
          "por_ia": {"claude": 7.5, "chatgpt": 0.0, ...},
          "ias_que_citaram": ["claude"],
          "ias_que_nao_citaram": ["chatgpt", "gemini", "perplexity"],
          "taxa_citacao_geral": 0.25   # % de perguntas onde citou
        }
        """

    def calcular_score_seo(self, checks: dict) -> ScoreDimensao:
        """
        Pontuação por check técnico:
        ssl:              1.5
        meta_description: 1.0
        canonical:        0.8
        viewport:         1.0
        sitemap:          1.5
        robots:           1.0
        open_graph:       0.8
        h1:               0.6
        conteudo_html:    1.8
        Total máximo:     10.0
        """

    def calcular_score_llmo(
        self, checks: dict, resultados: list[ResultadoIA]
    ) -> ScoreDimensao:
        """
        schema_ld:           2.0
        faq_schema:          2.5
        local_business:      2.5
        llms_txt:            3.0
        open_graph_completo: 0.5
        Bônus +1.0 se Perplexity citou com nível "detalhado"
        Cap: 10.0
        """

    def calcular_score_conteudo(self, checks: dict) -> ScoreDimensao:
        """
        h1_presente:          1.5
        estrutura_semantica:  1.5
        conteudo_substancial: 2.5   (>3000 chars de texto real)
        blog_ativo:           2.5
        Cap: 10.0
        """

    def calcular_score_geral(
        self,
        seo: ScoreDimensao,
        llmo: ScoreDimensao,
        autoridade: ScoreDimensao,
        conteudo: ScoreDimensao
    ) -> tuple[float, StatusEnum]:
        """
        score = soma(dimensao.pontuacao_ponderada)
        0.0–2.9 → critico
        3.0–4.9 → baixo
        5.0–6.9 → medio
        7.0–8.4 → bom
        8.5–10  → excelente
        """

    def gerar_resumo_executivo(
        self,
        request: DiagnosticoRequest,
        score_geral: float,
        status: StatusEnum,
        scores: dict,
        concorrentes: list[dict]
    ) -> str:
        """
        2–3 frases diretas. Exemplo:
        "{empresa} obteve score {score}/10 — {STATUS}. {n} IAs testadas,
        {k} citaram a empresa. Principal gap: {dimensao_mais_baixa}.
        {concorrente_principal} lidera as menções concorrentes."
        """
```

---

## PROMPT 10 — Gerador de relatório HTML

> **Antes de usar:** Crie e abra `/report/generator.py`. Cole no chat:

```
Escreva /report/generator.py.
Importe DiagnosticoResult de @models/schemas.py.

O relatório é HTML autocontido (CSS inline, sem dependências externas).
Paleta: navy #0d1b2a, gold #c9a84c, cream #f5f0e8,
        danger #e05c4b, amber #e0a030, success #4caf7d.

class ReportGenerator:

    def gerar_html(self, resultado: DiagnosticoResult) -> str:
        """
        Gera HTML completo com as seções abaixo NA ORDEM EXATA:

        ── SEÇÃO 1: CABEÇALHO
           Logo "Vértice Carioca" em texto estilizado (navy/gold)
           Nome da empresa + especialidade + cidade/estado
           Data do diagnóstico + IAs utilizadas como badges

        ── SEÇÃO 2: SCORES POR DIMENSÃO
           4 cards lado a lado (responsivo: 2×2 em mobile)
           Cada card: label da dimensão + peso % + número + barra de progresso
           Cor da barra: danger se <4, amber se <7, success se ≥7

        ── SEÇÃO 3: ANÁLISE POR IA
           Um bloco por IA: logo/nome + score médio + taxa de citação
           Tabela colapsável com: pergunta | resposta (resumida a 150 chars) |
           nível de citação (badge colorido) | pontuação
           Linha verde se citou, vermelha se não citou

        ── SEÇÃO 4: CONCORRENTES IDENTIFICADOS
           Título: "Empresas citadas pelas IAs no lugar de {empresa_nome}"
           Se lista vazia: "Nenhum concorrente identificado nas respostas"
           Se não vazia: tabela rankeada com nome + vezes citado
           Nota em itálico: "Estas empresas aparecem quando as IAs são
           perguntadas sobre {especialidade} em {cidade}."

        ── SEÇÃO 5: VERIFICAÇÕES TÉCNICAS
           Grid de 9 checks de SEO + 5 checks de LLMO
           ✓ verde (passou) ou ✗ vermelho (faltando) + label do check
           Agrupados com cabeçalho de categoria

        ── SEÇÃO 6: PLANO DE AÇÃO
           3 colunas: URGENTE (fundo danger) / 30 DIAS (fundo amber) /
                      CONTÍNUO (fundo success-dim)
           Card por ação com texto direto

        ── SEÇÃO 7: PRÓXIMOS PASSOS
           Tabela de planos da Vértice:
           Diagnóstico Pro R$497 | LLMO Starter R$1.197 | LLMO Completo R$2.997
           WhatsApp: (21) 99969-0903
           E-mail: verticecarioca@gmail.com

        ── SEÇÃO 8: DIAGNÓSTICO FINAL  ← ÚLTIMA SEÇÃO, CONCLUSÃO DO RELATÓRIO
           Bloco com borda dourada, padding generoso, visualmente destacado.

           Título: "Diagnóstico Final"
           Subtítulo: "Visibilidade nas IAs — {empresa_nome}"

           Nota geral: número em fonte 48px bold, seguido de "/10" em 24px
           Label de status: texto em caixa alta, 20px, cor por faixa:
             critico  → #e05c4b   CRÍTICO
             baixo    → #e0a030   BAIXO
             medio    → #e0c47a   MÉDIO
             bom      → #4caf7d   BOM
             excelente→ #4caf7d   EXCELENTE

           Parágrafo de interpretação (chamar gerar_interpretacao_final())

           Linha divisória fina dourada

           Rodapé: "Diagnóstico realizado por Vértice Carioca em {data}
           utilizando {ias_usadas}. Documento confidencial."
        """

    def gerar_interpretacao_final(
        self,
        score: float,
        status: str,
        empresa: str,
        especialidade: str,
        ias_que_nao_citaram: list[str],
        concorrentes: list[dict]
    ) -> str:
        """
        Retorna parágrafo de 2–3 frases adaptado à faixa de score.

        CRÍTICO (< 3.0):
        "{empresa} obteve nota {score}/10 — CRÍTICO. Isso significa que
        nenhuma das {n} IAs testadas a reconhece como referência em
        {especialidade}. Sua presença digital atual é insuficiente para
        ser encontrada por clientes que usam IA para buscar {especialidade}."

        BAIXO (3.0–4.9):
        "{empresa} obteve nota {score}/10 — BAIXO. As IAs têm conhecimento
        limitado sobre a empresa: foi citada em {pct}% das consultas, sem
        detalhes suficientes para gerar recomendações consistentes.
        {concorrente_principal} lidera as menções no segmento."

        MÉDIO (5.0–6.9):
        "{empresa} obteve nota {score}/10 — MÉDIO. A empresa é reconhecida
        por algumas IAs, mas ainda perde visibilidade em {gaps_principais}.
        Há margem significativa para avançar nas posições de recomendação."

        BOM (7.0–8.4):
        "{empresa} obteve nota {score}/10 — BOM. A empresa tem presença
        sólida e é citada com frequência pelas IAs. O foco agora é
        consolidar autoridade e ampliar citações com mais detalhes."

        EXCELENTE (≥ 8.5):
        "{empresa} obteve nota {score}/10 — EXCELENTE. A empresa está bem
        posicionada e é reconhecida como referência em {especialidade}
        pelas principais IAs. Recomenda-se monitoramento contínuo."

        Substitua {pct}, {gaps_principais}, {concorrente_principal}
        com dados reais do resultado.
        """

    def salvar_html(
        self, resultado: DiagnosticoResult, pasta: str = "outputs"
    ) -> str:
        # Cria a pasta se não existir
        # Salva o HTML e retorna o caminho completo do arquivo

    def gerar_nome_arquivo(self, resultado: DiagnosticoResult) -> str:
        # "LLMO_{EmpresaNome}_{YYYY-MM-DD}.html"
        # Sanitiza o nome da empresa (remove caracteres especiais)
```

---

## PROMPT 11 — Endpoints FastAPI

> **Antes de usar:**
> 1. Crie e abra `/api/routes.py`
> 2. Garanta que `/models/schemas.py` está salvo
> 3. Cole no chat:

```
Escreva /api/routes.py com todos os endpoints do sistema LLMO.
Importe modelos de @models/schemas.py.

Use APIRouter do FastAPI. Autenticação: HTTP Basic Auth com usuário/senha
de variável de ambiente (PAINEL_USUARIO, PAINEL_SENHA).
O endpoint GET /health NÃO requer autenticação.

────────────────────────────────────
GRUPO 1 — BANCO DE PERGUNTAS (/perguntas)
────────────────────────────────────

GET    /perguntas                 → list[Pergunta] com filtros via query params
GET    /perguntas/segmentos       → dict de segmentos e especialidades
GET    /perguntas/sugestao        → list[Pergunta] sugeridas (query: segmento, especialidade, limite)
GET    /perguntas/{id}            → Pergunta | 404
POST   /perguntas                 → Pergunta criada (body: texto, segmento, categoria, especialidade)
PUT    /perguntas/{id}            → Pergunta atualizada
DELETE /perguntas/{id}            → 204 (soft delete — desativa)
DELETE /perguntas/{id}/permanente → 204 (remove do banco)

────────────────────────────────────
GRUPO 2 — DIAGNÓSTICO (/diagnostico)
────────────────────────────────────

POST /diagnostico/estimar
  Body: DiagnosticoRequest
  Sem chamar IAs — só cálculo de custo e tempo
  Retorna: {custo_usd, custo_brl, tempo_estimado_seg,
            num_perguntas, num_ias, total_chamadas_api}

POST /diagnostico/iniciar
  Body: DiagnosticoRequest
  Valida que todos os perguntas_ids existem no banco
  Inicia diagnóstico em BackgroundTask
  Retorna imediatamente: {job_id: UUID, status: "iniciado"}

GET /diagnostico/{job_id}/status
  Retorna: {status: "rodando"|"concluido"|"erro",
            progresso: int (0–100),
            etapa_atual: str,
            erro: str | None}

GET /diagnostico/{job_id}/resultado
  Retorna DiagnosticoResult completo
  404 se job não existe; 425 se ainda rodando

GET /diagnostico/{job_id}/relatorio
  Content-Type: text/html
  Retorna HTML do relatório

GET /diagnostico/{job_id}/relatorio/download
  Content-Disposition: attachment; filename="LLMO_Empresa_Data.html"

────────────────────────────────────
GRUPO 3 — HISTÓRICO (/historico)
────────────────────────────────────

GET    /historico                → lista resumida (sem resultados_ias completos)
                                   query: segmento, cidade, limite=20, pagina=1
GET    /historico/{job_id}       → DiagnosticoResult completo do histórico
POST   /historico/{job_id}/fav   → toggle favorito
DELETE /historico/{job_id}       → remove do histórico

────────────────────────────────────
GRUPO 4 — SISTEMA
────────────────────────────────────

GET /health  (SEM autenticação)
  IMPORTANTE — health BARATO (sem custo de API, sem cold-start falso):
  NÃO chamar Anthropic/OpenAI/Google/Perplexity.
  Apenas validar:
  - variáveis de ambiente presentes (chave não vazia) → "configurado"|"ausente"
  - banco de perguntas legível em disco
  - pasta data/jobs gravável
  Retorna: {
    "status": "ok"|"degradado",
    "apis": {
      "claude": "configurado"|"ausente",
      "openai": "configurado"|"ausente",
      "gemini": "configurado"|"ausente",
      "perplexity": "configurado"|"ausente"
    },
    "banco_perguntas": {"total": int, "ativas": int},
    "jobs_store": "ok"|"erro"
  }

POST /sistema/testar-conexoes  (COM autenticação)
  Ping mínimo em cada API (1 chamada barata por provedor).
  Usado só pela tela Saúde → botão "Testar conexões".
  Retorna: {claude: "ok"|"erro", openai: "ok"|"erro",
            gemini: "ok"|"erro", perplexity: "ok"|"erro",
            detalhes: dict}

Middleware:
- Rate limit: máx 10 diagnósticos/hora (middleware simples com dict em memória)
- Log de todas as requisições com timestamp e duração

Armazenamento de jobs — PERSISTENTE EM DISCO (MVP):
  Pasta: data/jobs/
  Cada job: data/jobs/{job_id}.json
  Cache em memória: dict[UUID, dict] espelhado no disco a cada update
  Ao subir a app: carregar jobs concluídos dos últimos 90 dias do disco
  Assim restart do Railway NÃO apaga status/resultado/histórico.
  Formato do dict:
  # {"status": str, "progresso": int, "etapa": str,
  #  "resultado": DiagnosticoResult | None, "favorito": bool,
  #  "updated_at": iso8601}
  # TODO futuro: migrar para Redis/Postgres se volume > ~50 diag/dia
```

---

## PROMPT 12 — Painel interno

> **Antes de usar:** Crie e abra `/static/painel.html`. Cole no chat:

```
Escreva /static/painel.html — SPA completa em HTML/CSS/JS puro, sem framework.
Consome os endpoints da FastAPI via fetch().

Paleta: navy #0d1b2a, gold #c9a84c, cream #f5f0e8
Fontes via Google Fonts: Playfair Display (títulos) + DM Sans (corpo)
Layout: sidebar fixa à esquerda (200px) + área de conteúdo à direita
Responsivo: em mobile, sidebar vira menu hamburguer no topo

════════════════════════════════════
5 TELAS (ativadas pela sidebar)
════════════════════════════════════

TELA 1 — NOVO DIAGNÓSTICO
  Formulário em 3 passos com indicador de progresso (1/3 → 2/3 → 3/3):

  PASSO 1: Dados da empresa
    Nome da empresa (obrigatório)
    Razão social (opcional)
    URL do site (opcional, validar formato)
    Segmento (select: medicina / advocacia / psicologia / outro)
    Especialidade (texto)
    Cidade (texto, default "Rio de Janeiro")
    Estado (select, default RJ)
    IAs a usar (checkboxes: Claude ✓ ChatGPT ✓ Gemini ✓ Perplexity ✓)
    Botão "Próximo →" (valida campos obrigatórios antes de avançar)

  PASSO 2: Seleção de perguntas
    Ao carregar: fetch GET /perguntas/sugestao?segmento=X&especialidade=Y
    Exibir perguntas com checkboxes pré-marcados na sugestão
    Contador: "X perguntas selecionadas (mín. 5, máx. 20)"
    Filtros rápidos por categoria (botões toggle)
    Campo de busca por texto na pergunta
    Botão "+ Nova pergunta" → modal simples com campo de texto e categoria
      (POST /perguntas, adiciona ao banco e já marca como selecionada)
    Botão "← Voltar"
    Botão "Estimar custo →" → POST /diagnostico/estimar → exibe card
      com custo estimado em R$ e tempo estimado
    Botão "Iniciar Diagnóstico" (aparece só após estimar)

  PASSO 3: Progresso em tempo real
    Polling a cada 2s em GET /diagnostico/{id}/status
    Barra de progresso animada (0–100%)
    Log de etapas: "✓ Claude (10/10)" / "⟳ ChatGPT (6/10)..."
    Ao concluir: exibir score geral + status badge
    Botões: "Ver resultado completo" / "Baixar relatório HTML"

TELA 2 — RESULTADO
  Exibe o DiagnosticoResult do último diagnóstico ou do selecionado no histórico:
  Score geral grande + badge de status colorido
  Resumo executivo em itálico
  4 cards de dimensão com barras de progresso coloridas
  Acordeão por IA: clica para expandir e ver perguntas/respostas
    Cada linha: pergunta | nível de citação (badge) | pontuação
    Linha verde se citou, vermelha se não citou
  Tabela de concorrentes identificados
  Grid de checks técnicos (✓/✗)
  Plano de ação em 3 colunas
  Bloco destacado "Diagnóstico Final" com nota e interpretação
  Botão "Baixar relatório HTML"

TELA 3 — BANCO DE PERGUNTAS
  Filtros: segmento, especialidade, categoria, busca por texto, ativas/inativas
  Tabela com colunas: texto (60 chars) | segmento | especialidade |
    categoria (badge) | status (toggle ativa/inativa) | ações (editar/excluir)
  Botão "Nova pergunta" → modal de criação com preview em tempo real
    (substitui placeholders com dados de exemplo: empresa="Empresa Exemplo",
     cidade="Rio de Janeiro" etc.)
  Contador: "X perguntas ativas de Y total"

TELA 4 — HISTÓRICO
  Busca por nome de empresa
  Filtros: segmento, cidade, período (últimos 7/30/90 dias), favoritos
  Cards de diagnósticos:
    Nome + especialidade | Data | Score (número + badge colorido)
    Botões: Ver | Baixar | ★ Favorito | 🗑 Excluir
  Paginação (20 por página)

TELA 5 — SAÚDE DO SISTEMA
  4 cards de IAs com status de CONFIGURAÇÃO (verde=chave presente /
    vermelho=ausente) vindos de GET /health — sem custo de API
  Botão "Testar conexões" → POST /sistema/testar-conexoes (autenticado)
    → atualiza cards com ok/erro real de cada provedor
  Card do banco: total de perguntas, ativas, por segmento
  Card do store de jobs: ok/erro + qtd de jobs no disco
  Custo estimado por diagnóstico padrão (10 perguntas × 4 IAs)
  Total de diagnósticos rodados no mês
```

---

## PROMPT 13 — Testes

> **Antes de usar:**
> 1. Crie `/tests/__init__.py` e `/tests/test_sistema.py` (vazios)
> 2. Crie `/tests/mock_responses.py` (vazio)
> 3. Abra os dois arquivos no editor
> 4. Cole no chat:

```
Escreva os arquivos de teste para o sistema LLMO da Vértice.
Use @models/schemas.py, @prompts/banco.py, @prompts/substituidor.py,
@scoring/engine.py como referência.

────────────────────────────────────
ARQUIVO 1: /tests/mock_responses.py
────────────────────────────────────
Crie respostas simuladas de cada IA para 5 perguntas de teste,
variando entre citada e não citada:

MOCK_EMPRESA = "Clínica Exemplo Cirurgia Plástica"
MOCK_CIDADE = "Rio de Janeiro"

mock_citado_detalhado: resposta que menciona a empresa com endereço e serviço
mock_citado_superficial: resposta que cita só o nome
mock_vago: resposta que cita parte do nome
mock_nao_citado: resposta sobre o segmento sem citar a empresa
mock_com_concorrentes: resposta que cita 2 outras clínicas mas não a empresa

────────────────────────────────────
ARQUIVO 2: /tests/test_sistema.py
────────────────────────────────────
Use pytest e pytest-asyncio. Importe mocks de mock_responses.py.

Fixtures obrigatórias:
  empresa_request: DiagnosticoRequest com 10 UUIDs fictícios
  resultado_critico: DiagnosticoResult com score_geral=1.8, status=critico
  resultado_bom: DiagnosticoResult com score_geral=7.5, status=bom

Testes (18 no total):

BANCO DE PERGUNTAS:
  test_banco_seed_carrega           → len(perguntas) >= 50
  test_banco_filtro_segmento        → só retorna medicina
  test_banco_filtro_especialidade   → só retorna cirurgia plástica
  test_banco_sugestao_equilibrada   → 10 itens, pelo menos 1 de cada categoria principal
  test_banco_crud_ciclo_completo    → criar → editar → desativar → não aparece em listar

SUBSTITUIDOR:
  test_substituidor_sem_placeholders_residuais
    → nenhum {placeholder} restante após substituição

AVALIAÇÃO DE RESPOSTA:
  test_avaliar_detalhado    → citou=True, nivel=detalhado, pontuacao=10
  test_avaliar_superficial  → citou=True, nivel=superficial, pontuacao=6
  test_avaliar_vago         → citou=True, nivel=vago, pontuacao=3
  test_avaliar_nao_citado   → citou=False, nivel=nao_citado, pontuacao=0

SCORING:
  test_pesos_somam_1              → sum(PESOS_DIMENSAO.values()) == 1.0
  test_score_geral_calculo        → 8.0×0.25 + 2.0×0.30 + 1.0×0.25 + 5.0×0.20 == 4.15
  test_status_limites (parametrizado com 5 casos)
    → 1.5→critico, 3.0→baixo, 5.0→medio, 7.0→bom, 8.5→excelente

RELATÓRIO:
  test_report_contem_empresa        → empresa_nome no HTML gerado
  test_report_contem_diagnostico_final → "Diagnóstico Final" no HTML
  test_report_contem_nota_geral     → score_geral formatado no HTML
  test_report_secao_final_e_ultima  → "Diagnóstico Final" aparece DEPOIS de "Próximos Passos"

API (usando TestClient do FastAPI):
  test_health_retorna_200           → status 200, chaves em apis.*,
                                      NÃO exige chamadas reais a provedores
  test_health_nao_cobram_api        → mockar SDKs; health não deve chamá-los
```

---

## PROMPT 14 — Deploy no Railway

> **Antes de usar:**
> 1. Crie `Dockerfile`, `railway.toml`, `main.py`, `DEPLOY.md` (vazios)
> 2. Abra todos no editor
> 3. Cole no chat:

```
Escreva os 4 arquivos de deploy do sistema LLMO da Vértice no Railway.
Use @api/routes.py, @services/ e @static/painel.html como referência.

────────────────────────────────────
ARQUIVO 1: Dockerfile
────────────────────────────────────
Base: python:3.11-slim
- Instalar dependências do requirements.txt
- Copiar todo o código
- Criar /app/outputs e /app/data com mkdir -p
- Expor porta 8000
- CMD: uvicorn main:app --host 0.0.0.0 --port 8000

────────────────────────────────────
ARQUIVO 2: railway.toml
────────────────────────────────────
[build]
  builder = "DOCKERFILE"

[deploy]
  startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
  healthcheckPath = "/health"
  healthcheckTimeout = 30
  restartPolicyType = "ON_FAILURE"
  restartPolicyMaxRetries = 3

────────────────────────────────────
ARQUIVO 3: main.py
────────────────────────────────────
Entry point da aplicação FastAPI:
- Carregar variáveis de ambiente com python-dotenv
- Instanciar BancoPerguntas (carrega seed na primeira execução)
- Garantir pastas data/jobs e outputs (mkdir -p)
- Carregar jobs persistidos de data/jobs/*.json (últimos 90 dias)
- Instanciar ClaudeService, OpenAIService, GeminiService, PerplexityService
  com as chaves de variável de ambiente
- Instanciar SiteAuditor, ScoringEngine, ReportGenerator, LLMOOrchestrator
- Registrar router de /api/routes.py com prefixo /api
- Montar StaticFiles em /static
- GET "/" → retornar FileResponse de /static/painel.html
- GET "/health" → sem autenticação, barato (sem chamadas a APIs de IA)
- Incluir middleware de CORS (origens: * para desenvolvimento)
- Incluir middleware de logging de requisições

────────────────────────────────────
ARQUIVO 4: DEPLOY.md
────────────────────────────────────
Guia em português com os passos:

a. Subir código para GitHub (repositório privado recomendado)

b. Criar projeto no Railway (railway.app):
   New Project → Deploy from GitHub repo → selecionar o repositório

c. Adicionar variáveis de ambiente no Railway (Settings → Variables):
   ANTHROPIC_API_KEY   = sk-ant-...
   OPENAI_API_KEY      = sk-...
   GOOGLE_API_KEY      = ...
   PERPLEXITY_API_KEY  = pplx-...
   PAINEL_USUARIO      = catia
   PAINEL_SENHA        = [senha forte, mínimo 12 caracteres]

d. Adicionar volumes persistentes (Settings → Volumes):
   /app/data    → banco de perguntas + data/jobs/ (histórico sobrevive ao redeploy)
   /app/outputs → relatórios gerados
   SEM o volume /app/data, restart apaga perguntas customizadas e jobs.

e. Primeiro deploy:
   Railway faz build automático ao conectar o repositório.
   Acompanhar logs em tempo real no painel Railway.

f. Verificar funcionamento:
   Acessar URL gerada (ex: https://llmo-vertice.up.railway.app)
   Ir em Saúde do Sistema → Testar conexões
   Rodar um diagnóstico de teste antes de usar com clientes

CUSTO ESTIMADO NO RAILWAY:
  Plano Starter $5/mês: 500h execução + volumes persistentes
  Para 1–5 diagnósticos/dia: Starter é suficiente
  Para >10 diagnósticos/dia: considerar plano Pro $20/mês
```

---

## ORDEM DE EXECUÇÃO NO CURSOR

```
Sessão 1 — Base do projeto
  .cursor/rules/llmo-vertice.mdc (criar na raiz/.cursor/rules/)
  Prompt 1 (estrutura + arquivos de config)
  Prompt 2 (modelos Pydantic em /models/schemas.py)
  TESTAR: python -c "from models.schemas import DiagnosticoRequest; print('OK')"

Sessão 2 — Banco de perguntas
  Prompt 3 (/prompts/banco.py)
  Prompt 3B (/data/perguntas_seed.json + /prompts/substituidor.py)
  TESTAR no terminal:
    python -c "
    from prompts.banco import BancoPerguntas
    b = BancoPerguntas()
    print(f'{len(b.listar())} perguntas carregadas')
    sug = b.sugerir_para_diagnostico('medicina', 'cirurgia plástica')
    print(f'{len(sug)} sugeridas')
    "

Sessão 3 — Serviços de IA + auditor (5 prompts)
  Prompt 4 (Claude) → Prompt 5 (OpenAI) → Prompt 6 (Gemini) → Prompt 7 (Perplexity)
  Prompt 7B (/services/site_auditor.py)
  NÃO TESTAR IAs com API real ainda — só verificar que importa sem erros
  TESTAR auditor com URL pública (ex: https://example.com) se quiser

Sessão 4 — Lógica principal
  Prompt 8 (/services/orchestrator.py) — deve chamar SiteAuditor + ScoringEngine
  Prompt 9 (/scoring/engine.py)
  TESTAR com mocks (não gastar créditos de API):
    pytest tests/ -k "scoring or avaliar" -v

Sessão 5 — Saída
  Prompt 10 (/report/generator.py)
  Prompt 11 (/api/routes.py) — jobs em data/jobs/; /health barato
  TESTAR: uvicorn main:app --reload → GET http://localhost:8000/health

Sessão 6 — Painel
  Prompt 12 (/static/painel.html)
  TESTAR no browser: http://localhost:8000
  Rodar diagnóstico completo de teste com dados reais

Sessão 7 — Qualidade e entrega
  Prompt 13 (/tests/)
  Prompt 14 (Dockerfile + railway.toml + main.py + DEPLOY.md)
  pytest tests/ -v
  Deploy no Railway (volumes: /app/data e /app/outputs)
```

---

## DICAS DE USO NO CURSOR

```
1. .cursor/rules/ É A MEMÓRIA DO PROJETO
   Não use .cursorrules (legado). Crie .cursor/rules/llmo-vertice.mdc
   com alwaysApply: true. Mantenha a regra atualizada se o projeto evoluir.

2. ABRA OS ARQUIVOS RELEVANTES ANTES DE PERGUNTAR
   O Cursor enxerga melhor o que está aberto nas abas do editor.
   Antes de pedir o Prompt 8 (orquestrador), abra os 4 serviços,
   o site_auditor e os schemas — o Cursor vai importar corretamente.

3. USE @ PARA REFERENCIAR ARQUIVOS NO CHAT
   @models/schemas.py → faz o Cursor ler o arquivo antes de responder
   @services/claude_service.py → para pedir consistência de interface
   @.cursor/rules/llmo-vertice.mdc → reforça pesos/modelos se necessário

4. ACEITE CÓDIGO EM BLOCOS, NÃO LINHA A LINHA
   O Cursor oferece "Accept All" para aceitar todo o código gerado.
   Use-o — depois revise no editor se necessário.

5. CTRL+K PARA EDIÇÕES INLINE
   Selecione um trecho de código no editor → Ctrl+K → peça a mudança
   específica. Mais rápido que colar no chat para ajustes pequenos.

6. TERMINAL INTEGRADO PARA TESTAR (Ctrl+`)
   Rode os testes sem sair do Cursor.
   O erro aparece no terminal e você pode colar de volta no chat.

7. CUSTO OPERACIONAL
   10 perguntas × 4 IAs × 600 tokens = ~24.000 tokens/diagnóstico
   Custo por diagnóstico: R$ 0,80 – R$ 1,50
   100 diagnósticos/mês = R$ 80 – R$ 150 em APIs de IA
   Railway Starter: R$ 25/mês
   Total operacional: ~R$ 105 – R$ 175/mês
   GET /health NÃO deve consumir créditos de API.

8. MARGEM DA VÉRTICE
   Diagnóstico Pro (R$497): custo ~R$2 → margem ~R$495
   LLMO Starter (R$1.197): custo ~R$5 → margem depende do tempo de implementação

9. PESOS DAS IAs (não misturar com diagnóstico)
   Score: ChatGPT 40% > Gemini 25% > Perplexity 20% > Claude 15%.
   Perplexity peso menor no score, mas ausência = sinal URGENTE no plano
   de ação (web indexada em tempo real).

10. JOBS E RESTART
    Persistência em data/jobs/*.json. Sem volume Railway em /app/data,
    o redeploy apaga o histórico — confirme o volume no DEPLOY.md.
```

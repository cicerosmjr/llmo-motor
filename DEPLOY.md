# Deploy — Sistema LLMO Vértice Carioca

## Opção A — Railway (recomendado para diagnósticos longos)

Processo contínuo + volumes em disco. Melhor custo/benefício se o diagnóstico
chama várias IAs (pode passar de 60s).

### a. Subir código para GitHub
Repositório privado recomendado.

### b. Criar projeto no Railway
1. Acesse [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo → selecionar o repositório

### c. Variáveis de ambiente (Settings → Variables)

```
ANTHROPIC_API_KEY   = sk-ant-...
OPENAI_API_KEY      = sk-...
GOOGLE_API_KEY      = ...
PERPLEXITY_API_KEY  = pplx-...
PAINEL_USUARIO      = catia
PAINEL_SENHA        = [senha forte, mínimo 12 caracteres]
```

### d. Volumes persistentes (Settings → Volumes)

| Montagem     | Uso                                              |
|--------------|--------------------------------------------------|
| `/app/data`  | banco de perguntas + `data/jobs/` (histórico)    |
| `/app/outputs` | relatórios HTML gerados                        |

**Sem o volume `/app/data`, restart apaga perguntas customizadas e jobs.**

### e. Primeiro deploy
Railway faz build automático ao conectar o repositório.

### f. Verificar
1. URL gerada → login no painel
2. **Saúde do Sistema** → **Testar conexões**
3. Diagnóstico de teste

### Custo estimado
- Starter $5/mês: 500h + volumes — suficiente para 1–5 diagnósticos/dia

---

## Opção B — Vercel + Supabase

O filesystem da Vercel é **read-only**. Sem Supabase o import de `main.py`
falha com `OSError: [Errno 30] Read-only file system: 'data/jobs'`.

### 1. Criar projeto no Supabase
1. [supabase.com](https://supabase.com) → New project
2. SQL Editor → colar e rodar `sql/supabase_schema.sql`
3. Settings → API → copiar:
   - Project URL → `SUPABASE_URL`
   - `service_role` (secret) → `SUPABASE_SERVICE_ROLE_KEY`
   - **Nunca** exponha a service_role no frontend

### 2. Variáveis na Vercel (Project → Settings → Environment Variables)

```
ANTHROPIC_API_KEY
OPENAI_API_KEY
GOOGLE_API_KEY
PERPLEXITY_API_KEY
PAINEL_USUARIO
PAINEL_SENHA          # obrigatória e forte
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

### 3. Deploy
- `vercel.json` já aponta o entrypoint `main.py`
- Redeploy após setar as envs
- `GET /health` deve retornar `"persistencia": "supabase"` e `jobs_store: ok`

### 4. Limites importantes (Vercel)
- **Timeout** da função: Hobby ~10s, Pro até 60s (ou mais com Fluid Compute).
  Um diagnóstico completo (4 IAs × N perguntas) costuma **ultrapassar** esse limite.
- `BackgroundTasks` do FastAPI **não é confiável** em serverless: o processo
  pode congelar após a resposta HTTP.
- Para uso real de diagnóstico na Vercel, planeje fila/worker (Inngest, QStash,
  etc.) ou use Railway para a API que roda o job.

Relatórios HTML são gerados sob demanda a partir do JSON do job (não dependem
de `outputs/` persistente). Na Vercel, gravação em disco usa `/tmp` (efêmero).

### 5. Auth
Todas as rotas `/api/*` (exceto `/api/health`) exigem Basic Auth com
`PAINEL_USUARIO` / `PAINEL_SENHA`. Sem senha forte, qualquer um que achar a URL
consome créditos das APIs pagas.

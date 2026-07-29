# Deploy no Railway — Sistema LLMO Vértice Carioca

## Passos

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
Acompanhe os logs em tempo real no painel.

### f. Verificar funcionamento
1. Acessar a URL gerada (ex: `https://llmo-vertice.up.railway.app`)
2. Ir em **Saúde do Sistema** → **Testar conexões**
3. Rodar um diagnóstico de teste antes de usar com clientes

## Custo estimado no Railway

- Plano Starter $5/mês: 500h execução + volumes persistentes
- Para 1–5 diagnósticos/dia: Starter é suficiente
- Para >10 diagnósticos/dia: considerar plano Pro $20/mês

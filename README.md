# Sistema LLMO — Vértice Carioca

Mede a visibilidade de empresas nas IAs (ChatGPT, Gemini, Perplexity, Claude).

## Setup local

1. Clonar o repositório
2. Criar venv e instalar dependências:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` para `.env` e preencher as chaves
4. Inicializar o banco de perguntas:
   ```bash
   python -c "from data.seed import inicializar; inicializar()"
   ```
5. Subir a API e abrir o painel:
   ```bash
   uvicorn main:app --reload
   ```
   Acesse http://localhost:8000

## Estrutura

```
api/          # Rotas FastAPI
services/     # IAs + auditor + orquestrador
prompts/      # Banco de perguntas e substituidor
scoring/      # Engine de pontuação
report/       # Gerador de relatório HTML
models/       # Schemas Pydantic
data/         # Seed + jobs persistentes
static/       # Painel interno
tests/        # Pytest
```

## Deploy

Ver [DEPLOY.md](DEPLOY.md).

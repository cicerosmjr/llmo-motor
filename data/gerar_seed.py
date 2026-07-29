"""Gera data/perguntas_seed.json com ≥8 perguntas por combinação."""

from __future__ import annotations

import json
from pathlib import Path

CATEGORIAS = [
    "reconhecimento",
    "recomendacao",
    "reputacao",
    "servicos",
    "localizacao",
    "generica",
]

COMBINACOES = [
    ("medicina", "geral"),
    ("medicina", "cirurgia plástica"),
    ("medicina", "dermatologia"),
    ("medicina", "odontologia"),
    ("medicina", "psiquiatria"),
    ("advocacia", "geral"),
    ("advocacia", "direito tributário"),
    ("advocacia", "direito imobiliário"),
    ("advocacia", "planejamento patrimonial"),
    ("advocacia", "direito trabalhista"),
    ("psicologia", "geral"),
    ("psicologia", "ansiedade e depressão"),
    ("psicologia", "psicologia infantil"),
    ("geral", None),
]

TEMPLATES = {
    "reconhecimento": [
        "Você conhece a empresa {empresa}, especializada em {especialidade} em {cidade}/{estado}?",
        "O que você sabe sobre {empresa} e seus serviços de {especialidade}?",
    ],
    "recomendacao": [
        "Quais são as melhores opções de {especialidade} em {cidade}? Inclua {empresa} se for relevante.",
        "Você recomendaria {empresa} para alguém buscando {especialidade} em {cidade}/{estado}?",
    ],
    "reputacao": [
        "Qual a reputação de {empresa} na área de {especialidade}?",
        "Há avaliações ou menções positivas sobre {empresa} em {cidade}?",
    ],
    "servicos": [
        "Quais serviços de {especialidade} a {empresa} oferece?",
        "A {empresa} atende pacientes/clientes buscando {especialidade} em {cidade}?",
    ],
    "localizacao": [
        "Onde fica a {empresa} em {cidade}/{estado}? Ela atende na região?",
    ],
    "generica": [
        "Como encontrar bons profissionais de {especialidade} em {cidade}/{estado}?",
    ],
}

# templates extras para fechar ≥8 por combinação
EXTRAS = [
    ("reconhecimento", "A {empresa} ({site_url}) é referência em {especialidade}?"),
    ("recomendacao", "Liste clínicas/escritórios de {especialidade} em {cidade}, incluindo {empresa} se souber."),
    ("reputacao", "Existem reclamações conhecidas sobre {empresa} em {especialidade}?"),
    ("servicos", "A {empresa} oferece atendimento online ou presencial de {especialidade} em {cidade}?"),
]


def gerar() -> list[dict]:
    perguntas: list[dict] = []
    for segmento, especialidade in COMBINACOES:
        esp = especialidade or "geral"
        batch: list[dict] = []
        for cat in CATEGORIAS:
            for texto in TEMPLATES[cat]:
                batch.append(
                    {
                        "texto": texto,
                        "segmento": segmento,
                        "especialidade": esp if segmento != "geral" else "geral",
                        "categoria": cat,
                        "ativa": True,
                        "criada_por": "vertice",
                    }
                )
        for cat, texto in EXTRAS:
            batch.append(
                {
                    "texto": texto,
                    "segmento": segmento,
                    "especialidade": esp if segmento != "geral" else "geral",
                    "categoria": cat,
                    "ativa": True,
                    "criada_por": "vertice",
                }
            )
        # Garante ≥8
        while len(batch) < 8:
            batch.append(
                {
                    "texto": f"Conte o que sabe sobre {{empresa}} em {{cidade}} no segmento de {esp}.",
                    "segmento": segmento,
                    "especialidade": esp if segmento != "geral" else "geral",
                    "categoria": "generica",
                    "ativa": True,
                    "criada_por": "vertice",
                }
            )
        perguntas.extend(batch[:12])  # até 12 por combinação
    return perguntas


if __name__ == "__main__":
    path = Path("data/perguntas_seed.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gerar()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gerado {len(data)} perguntas em {path}")

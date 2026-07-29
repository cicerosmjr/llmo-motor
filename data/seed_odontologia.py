"""
Seed: segmento Odontologia + perguntas Atelier Bucal (Bloco 1 — rodadas R1–R5).

Placeholders:
  {empresa}  ← Nome da empresa (passo 1)
  {cidade}   ← Cidade (passo 1)
  {bairro}   ← Bairro (passo 1)
  {estado}, {especialidade}, {site_url}

Uso (na pasta llmo, com o venv ativo):
    python data/seed_odontologia.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from prompts.banco import BancoPerguntas  # noqa: E402

# Rodadas da planilha (Perguntas + Resultados):
# R1 genérica | R2 intenção | R3 bairro | R4 nome direto | R5 comparação/lista

PERGUNTAS: list[dict] = [
    # ── R1 — Genérica (sem nome) — 4 perguntas ──
    {
        "texto": "Qual clínica odontológica de estética dental você recomenda em {cidade}?",
        "especialidade": "odontologia geral",
        "categoria": "recomendacao",
        "rodada": "r1",
    },
    {
        "texto": "Me indica um dentista especializado em facetas de porcelana em {cidade}.",
        "especialidade": "facetas de porcelana",
        "categoria": "recomendacao",
        "rodada": "r1",
    },
    {
        "texto": "Qual é a melhor clínica de clareamento dental em {cidade}?",
        "especialidade": "clareamento dental",
        "categoria": "recomendacao",
        "rodada": "r1",
    },
    {
        "texto": "Preciso fazer implante dentário em {cidade}. Qual clínica você recomenda?",
        "especialidade": "implante dentário",
        "categoria": "recomendacao",
        "rodada": "r1",
    },
    # ── R2 — Intenção real — 3 perguntas ──
    {
        "texto": "Quero transformar meu sorriso em {cidade}. Qual dentista ou clínica é referência nisso?",
        "especialidade": "odontologia geral",
        "categoria": "recomendacao",
        "rodada": "r2",
    },
    {
        "texto": (
            "Estou procurando uma clínica odontológica diferenciada em {cidade} "
            "— não clínica popular de shopping. O que você indica?"
        ),
        "especialidade": "odontologia geral",
        "categoria": "recomendacao",
        "rodada": "r2",
    },
    {
        "texto": "Dentista de estética em {cidade} com boas avaliações — quais você conhece?",
        "especialidade": "odontologia geral",
        "categoria": "reputacao",
        "rodada": "r2",
    },
    # ── R3 — Por bairro — 3 perguntas ──
    {
        "texto": "Dentista de estética no BAIRRO {bairro} em {cidade} — qual você recomenda?",
        "especialidade": "odontologia geral",
        "categoria": "localizacao",
        "rodada": "r3",
    },
    {
        "texto": "Clínica odontológica em {bairro} {cidade} — alguma indicação?",
        "especialidade": "odontologia geral",
        "categoria": "localizacao",
        "rodada": "r3",
    },
    {
        "texto": (
            "Qual dentista especializado em facetas de porcelana você "
            "conhece na região do {bairro} em {cidade}?"
        ),
        "especialidade": "facetas de porcelana",
        "categoria": "localizacao",
        "rodada": "r3",
    },
    # ── R4 — Nome direto — 3 perguntas ──
    {
        "texto": "Você conhece o {empresa} em {cidade}? O que sabe sobre essa clínica?",
        "especialidade": "odontologia geral",
        "categoria": "reconhecimento",
        "rodada": "r4",
    },
    {
        "texto": "O {empresa} é uma clínica odontológica confiável em {cidade}?",
        "especialidade": "odontologia geral",
        "categoria": "reputacao",
        "rodada": "r4",
    },
    {
        "texto": "Me conta sobre o {empresa} — dentista {cidade}.",
        "especialidade": "odontologia geral",
        "categoria": "reconhecimento",
        "rodada": "r4",
    },
    # ── R5 — Comparação / lista — 3 perguntas ──
    {
        "texto": "Quais são as melhores clínicas de odontologia estética de {cidade}? Me dá uma lista.",
        "especialidade": "odontologia geral",
        "categoria": "recomendacao",
        "rodada": "r5",
    },
    {
        "texto": "Compare clínicas de estética dental de alto padrão em {cidade}.",
        "especialidade": "odontologia geral",
        "categoria": "recomendacao",
        "rodada": "r5",
    },
    {
        "texto": (
            "Quais dentistas de {cidade} são referência em facetas de "
            "porcelana e lentes de contato dental?"
        ),
        "especialidade": "facetas de porcelana",
        "categoria": "recomendacao",
        "rodada": "r5",
    },
]


def _chave_match(texto: str) -> str:
    """Normaliza texto para casar versões antigas (São Paulo/IPIRANGA) com placeholders."""
    t = texto.strip().lower()
    t = t.replace("são paulo", "{cidade}").replace("sao paulo", "{cidade}")
    t = re.sub(r"\bsp\b", "{cidade}", t)
    t = t.replace("ipiranga", "{bairro}")
    t = re.sub(r"\s+", " ", t)
    return t


def encontrar(banco: BancoPerguntas, texto: str):
    chave = _chave_match(texto)
    for p in banco._perguntas:
        if p.segmento.lower() != "odontologia":
            continue
        if p.texto.strip().lower() == texto.strip().lower():
            return p
        if _chave_match(p.texto) == chave:
            return p
    return None


def main() -> None:
    banco = BancoPerguntas()
    criadas = 0
    atualizadas = 0
    puladas = 0

    for item in PERGUNTAS:
        existente = encontrar(banco, item["texto"])
        rodada = item.get("rodada")
        if existente is None:
            banco.criar(
                texto=item["texto"],
                segmento="odontologia",
                categoria=item["categoria"],
                especialidade=item["especialidade"],
                rodada=rodada,
            )
            criadas += 1
            continue

        mudou = (
            existente.texto != item["texto"]
            or (existente.rodada.value if existente.rodada else None) != rodada
            or existente.categoria.value != item["categoria"]
            or (existente.especialidade or "") != item["especialidade"]
        )
        if mudou:
            dados = {
                "texto": item["texto"],
                "categoria": item["categoria"],
                "especialidade": item["especialidade"],
                "rodada": rodada,
            }
            banco.atualizar(existente.id, dados)
            atualizadas += 1
        else:
            puladas += 1

    com_rodada = [
        p for p in banco._perguntas
        if p.segmento.lower() == "odontologia" and p.rodada and p.ativa
    ]
    por_r: dict[str, int] = {}
    for p in com_rodada:
        assert p.rodada is not None
        por_r[p.rodada.value] = por_r.get(p.rodada.value, 0) + 1

    print("=== Seed Odontologia (placeholders cidade/bairro/empresa) ===")
    print(f"Perguntas criadas: {criadas}")
    print(f"Atualizadas: {atualizadas}")
    print(f"Já ok (puladas): {puladas}")
    print(f"Por rodada: {dict(sorted(por_r.items()))}")
    print()
    print("Passo 1 do diagnóstico:")
    print("  Nome da empresa → {empresa}")
    print("  Cidade → {cidade}")
    print("  Bairro → {bairro}  (ex.: Ipiranga)")


if __name__ == "__main__":
    main()

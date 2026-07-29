"""Inicialização do banco de perguntas a partir do seed."""

from __future__ import annotations

from prompts.banco import BancoPerguntas


def inicializar() -> int:
    banco = BancoPerguntas()
    total = len(banco.listar())
    print(f"Banco inicializado com {total} perguntas ativas")
    return total


if __name__ == "__main__":
    inicializar()

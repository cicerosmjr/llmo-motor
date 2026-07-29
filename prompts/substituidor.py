"""Substituição de placeholders nas perguntas do diagnóstico."""

from __future__ import annotations

from uuid import UUID

from models.schemas import DiagnosticoRequest, Pergunta


def substituir_placeholders(
    texto: str,
    empresa: str,
    especialidade: str,
    cidade: str,
    estado: str,
    site_url: str | None = None,
    bairro: str | None = None,
) -> str:
    site = site_url if site_url else empresa
    bairro_val = bairro if bairro else cidade
    return (
        texto.replace("{empresa}", empresa)
        .replace("{especialidade}", especialidade)
        .replace("{cidade}", cidade)
        .replace("{bairro}", bairro_val)
        .replace("{estado}", estado)
        .replace("{site_url}", site)
    )


def preparar_perguntas_diagnostico(
    perguntas: list[Pergunta],
    request: DiagnosticoRequest,
) -> list[tuple[UUID, str]]:
    return [
        (
            p.id,
            substituir_placeholders(
                p.texto,
                empresa=request.empresa_nome,
                especialidade=request.especialidade,
                cidade=request.cidade,
                estado=request.estado,
                site_url=request.site_url,
                bairro=request.bairro,
            ),
        )
        for p in perguntas
    ]

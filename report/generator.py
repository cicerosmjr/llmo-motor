"""Gerador de relatório HTML autocontido."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from models.schemas import DiagnosticoResult, StatusEnum, label_nivel_citacao


CORES_STATUS = {
    "critico": "#e05c4b",
    "baixo": "#e0a030",
    "medio": "#e0c47a",
    "bom": "#4caf7d",
    "excelente": "#4caf7d",
}

LABELS_STATUS = {
    "critico": "CRÍTICO",
    "baixo": "BAIXO",
    "medio": "MÉDIO",
    "bom": "BOM",
    "excelente": "EXCELENTE",
}


class ReportGenerator:
    def gerar_html(self, resultado: DiagnosticoResult) -> str:
        req = resultado.request
        status = resultado.status.value
        cor = CORES_STATUS.get(status, "#e0a030")
        label = LABELS_STATUS.get(status, status.upper())
        data = resultado.created_at.strftime("%d/%m/%Y %H:%M")
        ias = ", ".join(req.ias_ativas)

        autoridade = resultado.scores.get("autoridade_citacao")
        ias_nao = (
            autoridade.detalhes.get("ias_que_nao_citaram", []) if autoridade else []
        )
        interpretacao = self.gerar_interpretacao_final(
            resultado.score_geral,
            status,
            req.empresa_nome,
            req.especialidade,
            ias_nao,
            resultado.concorrentes_mais_citados,
        )

        scores_html = self._secao_scores(resultado)
        bloco1_html = self._secao_bloco1(resultado)
        planilha_html = self._secao_planilha(resultado)
        ias_html = self._secao_ias(resultado)
        conc_html = self._secao_concorrentes(resultado)
        checks_html = self._secao_checks(resultado)
        plano_html = self._secao_plano(resultado)

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>LLMO — {req.empresa_nome}</title>
<style>
  :root {{ --navy:#0d1b2a; --gold:#c9a84c; --cream:#f5f0e8; --danger:#e05c4b; --amber:#e0a030; --success:#4caf7d; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Georgia, serif; background:var(--cream); color:var(--navy); }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 20px; }}
  h1,h2,h3 {{ font-family:Georgia, serif; }}
  .logo {{ font-size:28px; font-weight:700; color:var(--navy); }}
  .logo span {{ color:var(--gold); }}
  .badge {{ display:inline-block; padding:4px 10px; border-radius:4px; background:var(--navy); color:var(--cream); font-size:12px; margin:2px; }}
  .grid4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
  @media(max-width:700px){{ .grid4 {{ grid-template-columns:1fr 1fr; }} }}
  .card {{ background:#fff; border:1px solid #e5dfd3; padding:16px; }}
  .bar {{ height:8px; background:#e5dfd3; border-radius:4px; margin-top:8px; }}
  .bar > i {{ display:block; height:100%; border-radius:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th,td {{ border-bottom:1px solid #e5dfd3; padding:8px; text-align:left; vertical-align:top; }}
  .ok {{ background:#eaf7ef; }}
  .nok {{ background:#fcecea; }}
  .checks {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
  .plano {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }}
  .urg {{ background:#fcecea; padding:12px; }}
  .d30 {{ background:#fff6e5; padding:12px; }}
  .cont {{ background:#eaf7ef; padding:12px; }}
  .final {{ border:2px solid var(--gold); padding:32px; background:#fff; margin-top:32px; text-align:center; }}
  .nota {{ font-size:48px; font-weight:700; }}
  .nota small {{ font-size:24px; }}
  .status-label {{ font-size:20px; letter-spacing:2px; }}
  .next table td {{ font-size:15px; }}
  .bloco1 {{ border:1px solid var(--gold); background:#fff; padding:20px; margin:16px 0; }}
  .bloco1 .media {{ font-size:36px; font-weight:700; color:var(--navy); }}
</style>
</head>
<body>
<div class="wrap">
  <section>
    <div class="logo">Vértice <span>Carioca</span></div>
    <h1>{req.empresa_nome}</h1>
    <p>{req.especialidade} — {req.cidade}/{req.estado}</p>
    <p>Diagnóstico em {data}</p>
    <p>{''.join(f'<span class="badge">{ia}</span>' for ia in req.ias_ativas)}</p>
  </section>

  <section>
    <h2>Scores por dimensão</h2>
    {scores_html}
  </section>

  {bloco1_html}

  {planilha_html}

  <section>
    <h2>Análise por IA</h2>
    {ias_html}
  </section>

  <section>
    <h2>Empresas citadas pelas IAs no lugar de {req.empresa_nome}</h2>
    {conc_html}
  </section>

  <section>
    <h2>Verificações técnicas</h2>
    {checks_html}
  </section>

  <section>
    <h2>Plano de ação</h2>
    {plano_html}
  </section>

  <section class="next">
    <h2>Próximos Passos</h2>
    <table>
      <tr><td>Diagnóstico Pro</td><td>R$497</td></tr>
      <tr><td>LLMO Starter</td><td>R$1.197</td></tr>
      <tr><td>LLMO Completo</td><td>R$2.997</td></tr>
    </table>
    <p>WhatsApp: (21) 99969-0903 · E-mail: verticecarioca@gmail.com</p>
  </section>

  <section class="final">
    <h2>Diagnóstico Final</h2>
    <p>Visibilidade nas IAs — {req.empresa_nome}</p>
    <div class="nota">{resultado.score_geral:.1f}<small>/10</small></div>
    <div class="status-label" style="color:{cor}">{label}</div>
    <p style="max-width:640px;margin:16px auto;text-align:left">{interpretacao}</p>
    <hr style="border:none;border-top:1px solid var(--gold);margin:24px 0"/>
    <p style="font-size:13px;opacity:.8">Diagnóstico realizado por Vértice Carioca em {data}
    utilizando {ias}. Documento confidencial.</p>
  </section>
</div>
</body>
</html>"""

    def _cor_barra(self, valor: float) -> str:
        if valor < 4:
            return "#e05c4b"
        if valor < 7:
            return "#e0a030"
        return "#4caf7d"

    def _secao_scores(self, resultado: DiagnosticoResult) -> str:
        cards = []
        for nome, score in resultado.scores.items():
            pct = max(0, min(100, score.pontuacao_bruta * 10))
            cor = self._cor_barra(score.pontuacao_bruta)
            cards.append(
                f"""<div class="card">
                <div>{nome.replace('_',' ').title()}</div>
                <div style="font-size:12px">peso {int(score.peso*100)}%</div>
                <div style="font-size:28px;font-weight:700">{score.pontuacao_bruta:.1f}</div>
                <div class="bar"><i style="width:{pct}%;background:{cor}"></i></div>
                </div>"""
            )
        return f'<div class="grid4">{"".join(cards)}</div>'

    def _secao_bloco1(self, resultado: DiagnosticoResult) -> str:
        b1 = resultado.bloco1_visibilidade
        if b1 is None:
            return ""
        media_txt = f"{b1.media:.1f}" if b1.media is not None else "—"
        rows = []
        for n in b1.por_ia:
            if not n.disponivel:
                rows.append(
                    f"<tr class='nok'><td>{n.ia_nome}</td><td>—</td>"
                    f"<td>Indisponível</td><td>{n.motivo or ''}</td></tr>"
                )
                continue
            rodadas = ", ".join(r.upper() for r in n.rodadas_com_aparicao) or "nenhuma"
            nota = f"{n.nota:.0f}" if n.nota is not None else "—"
            rows.append(
                f"<tr class='{'ok' if (n.nota or 0) > 0 else 'nok'}'>"
                f"<td>{n.ia_nome}</td><td>{nota}</td>"
                f"<td>{rodadas}</td><td>{(n.evidencias[0] if n.evidencias else '')}</td></tr>"
            )
        return f"""<section class="bloco1">
          <h2>Bloco 1 — Visibilidade nas IAs</h2>
          <p>Média simples das notas por IA (rodadas R1–R5). Não altera o score geral.</p>
          <div class="media">{media_txt}<small>/10</small></div>
          <p><strong>{b1.interpretacao_label}</strong>
          · {b1.ias_avaliadas} IA(s) avaliadas
          {(' · indisponíveis: ' + ', '.join(b1.ias_indisponiveis)) if b1.ias_indisponiveis else ''}</p>
          <table>
            <tr><th>IA</th><th>Nota</th><th>Rodadas</th><th>Evidência</th></tr>
            {''.join(rows)}
          </table>
          <p style="font-size:12px;opacity:.75;margin-top:8px">
            Interpretação: 0–3 Invisível · 4–5 Existência básica · 6–7 Buscas específicas ·
            8–9 Recomendado ativamente · 10 Referência dominante
          </p>
        </section>"""

    def _secao_planilha(self, resultado: DiagnosticoResult) -> str:
        plan = resultado.diagnostico_planilha
        if plan is None:
            return ""
        # Só exibe detalhes manuais se houver pelo menos uma nota salva
        tem_notas = bool(plan.notas_salvas)
        st = plan.score_total
        if not tem_notas and (st is None or st.media is None or len(st.blocos_no_calculo) <= 1):
            # Apenas Bloco 1 — seção dedicada já cobre; evita duplicar total vazio
            if st and st.media is not None and st.blocos_no_calculo == ["bloco1"]:
                return f"""<section class="bloco1">
                  <h2>SCORE TOTAL LLMO</h2>
                  <p>Por enquanto só o Bloco 1 entrou no cálculo (blocos 2–6 ainda não preenchidos).</p>
                  <div class="media">{st.media:.1f}<small>/10</small></div>
                  <p><strong>{st.interpretacao_label}</strong></p>
                </section>"""
            return ""

        partes = []
        for bloco in plan.blocos_manuais:
            rows = []
            for c in bloco.criterios:
                nota = f"{c.nota:.0f}" if c.nota is not None else "—"
                rows.append(
                    f"<tr><td>{c.label}</td><td>{nota}</td>"
                    f"<td>{c.status.value}</td></tr>"
                )
            media = f"{bloco.media:.1f}" if bloco.media is not None else "—"
            partes.append(
                f"<h3>Bloco {bloco.numero} — {bloco.titulo}</h3>"
                f"<table><tr><th>Critério</th><th>Nota</th><th>Status</th></tr>"
                f"{''.join(rows)}</table>"
                f"<p><strong>SCORE MÉDIO — Bloco {bloco.numero}:</strong> {media}</p>"
            )

        total_html = ""
        if st and st.media is not None:
            total_html = f"""
              <div class="final" style="margin-top:16px">
                <h2>SCORE TOTAL LLMO</h2>
                <div class="nota">{st.media:.1f}<small>/10</small></div>
                <p><strong>{st.interpretacao_label}</strong></p>
                <p style="font-size:12px">Blocos no cálculo: {', '.join(st.blocos_no_calculo)}</p>
              </div>"""

        return f"""<section class="bloco1">
          <h2>Diagnóstico LLMO — Blocos manuais</h2>
          {''.join(partes)}
          {total_html}
        </section>"""

    def _secao_ias(self, resultado: DiagnosticoResult) -> str:
        por_ia: dict[str, list] = {}
        for r in resultado.resultados_ias:
            por_ia.setdefault(r.ia_nome, []).append(r)
        blocos = []
        for ia, items in por_ia.items():
            media = sum(i.pontuacao for i in items) / len(items) if items else 0
            taxa = sum(1 for i in items if i.citou_empresa) / len(items) if items else 0
            rows = []
            for i in items:
                cls = "ok" if i.citou_empresa else "nok"
                resp = (i.resposta_completa or "")[:150]
                rows.append(
                    f"<tr class='{cls}'><td>{i.pergunta_texto[:80]}</td>"
                    f"<td>{resp}</td><td>{label_nivel_citacao(i.nivel_citacao)}</td>"
                    f"<td>{i.pontuacao}</td></tr>"
                )
            blocos.append(
                f"<div class='card' style='margin-bottom:12px'><h3>{ia.title()}</h3>"
                f"<p>Score médio: {media:.1f} · Taxa de citação: {taxa:.0%}</p>"
                f"<table><tr><th>Pergunta</th><th>Resposta</th><th>Nível</th><th>Pts</th></tr>"
                f"{''.join(rows)}</table></div>"
            )
        return "".join(blocos) or "<p>Sem resultados de IA.</p>"

    def _secao_concorrentes(self, resultado: DiagnosticoResult) -> str:
        req = resultado.request
        if not resultado.concorrentes_mais_citados:
            return "<p>Nenhum concorrente identificado nas respostas</p>"
        rows = "".join(
            f"<tr><td>{i+1}</td><td>{c['nome']}</td><td>{c['vezes_citado']}</td></tr>"
            for i, c in enumerate(resultado.concorrentes_mais_citados)
        )
        return (
            f"<table><tr><th>#</th><th>Nome</th><th>Vezes citado</th></tr>{rows}</table>"
            f"<p><em>Estas empresas aparecem quando as IAs são perguntadas sobre "
            f"{req.especialidade} em {req.cidade}.</em></p>"
        )

    def _secao_checks(self, resultado: DiagnosticoResult) -> str:
        partes = []
        for dim, titulo in (
            ("seo_tecnico", "SEO técnico"),
            ("llmo_schema", "LLMO / Schema"),
            ("conteudo", "Conteúdo"),
        ):
            score = resultado.scores.get(dim)
            checks = (score.detalhes or {}).get("checks", {}) if score else {}
            itens = []
            for k, v in checks.items():
                mark = "✓" if v else "✗"
                cor = "#4caf7d" if v else "#e05c4b"
                itens.append(
                    f"<div style='color:{cor}'>{mark} {k.replace('_',' ')}</div>"
                )
            if not itens:
                itens.append("<div>Sem checks</div>")
            partes.append(f"<h3>{titulo}</h3><div class='checks'>{''.join(itens)}</div>")
        return "".join(partes)

    def _secao_plano(self, resultado: DiagnosticoResult) -> str:
        buckets = {"urgente": [], "30_dias": [], "continuo": []}
        for a in resultado.plano_acao:
            buckets.setdefault(a.get("prioridade", "continuo"), []).append(a["acao"])

        def bloco(titulo: str, chave: str, cls: str) -> str:
            lis = "".join(f"<li>{x}</li>" for x in buckets.get(chave, []))
            return f"<div class='{cls}'><strong>{titulo}</strong><ul>{lis or '<li>—</li>'}</ul></div>"

        return (
            "<div class='plano'>"
            + bloco("URGENTE", "urgente", "urg")
            + bloco("30 DIAS", "30_dias", "d30")
            + bloco("CONTÍNUO", "continuo", "cont")
            + "</div>"
        )

    def gerar_interpretacao_final(
        self,
        score: float,
        status: str,
        empresa: str,
        especialidade: str,
        ias_que_nao_citaram: list[str],
        concorrentes: list[dict],
    ) -> str:
        conc = concorrentes[0]["nome"] if concorrentes else "nenhum concorrente claro"
        n = max(1, len(ias_que_nao_citaram) + (4 - len(ias_que_nao_citaram)))
        # n IAs testadas aproximado
        n_testadas = len(ias_que_nao_citaram)  # incompleto; melhor usar score status
        if status == StatusEnum.critico.value or score < 3.0:
            return (
                f"{empresa} obteve nota {score}/10 — CRÍTICO. Isso significa que "
                f"as IAs testadas não a reconhecem como referência em "
                f"{especialidade}. Sua presença digital atual é insuficiente para "
                f"ser encontrada por clientes que usam IA para buscar {especialidade}."
            )
        if score < 5.0:
            return (
                f"{empresa} obteve nota {score}/10 — BAIXO. As IAs têm conhecimento "
                f"limitado sobre a empresa: a citação ocorre de forma inconsistente, "
                f"sem detalhes suficientes para gerar recomendações. "
                f"{conc} lidera as menções no segmento."
            )
        if score < 7.0:
            gaps = ", ".join(ias_que_nao_citaram) if ias_que_nao_citaram else "algumas dimensões"
            return (
                f"{empresa} obteve nota {score}/10 — MÉDIO. A empresa é reconhecida "
                f"por algumas IAs, mas ainda perde visibilidade em {gaps}. "
                f"Há margem significativa para avançar nas posições de recomendação."
            )
        if score < 8.5:
            return (
                f"{empresa} obteve nota {score}/10 — BOM. A empresa tem presença "
                f"sólida e é citada com frequência pelas IAs. O foco agora é "
                f"consolidar autoridade e ampliar citações com mais detalhes."
            )
        return (
            f"{empresa} obteve nota {score}/10 — EXCELENTE. A empresa está bem "
            f"posicionada e é reconhecida como referência em {especialidade} "
            f"pelas principais IAs. Recomenda-se monitoramento contínuo."
        )

    def salvar_html(self, resultado: DiagnosticoResult, pasta: str = "outputs") -> str:
        path = Path(pasta)
        path.mkdir(parents=True, exist_ok=True)
        nome = self.gerar_nome_arquivo(resultado)
        destino = path / nome
        destino.write_text(self.gerar_html(resultado), encoding="utf-8")
        return str(destino.resolve())

    def gerar_nome_arquivo(self, resultado: DiagnosticoResult) -> str:
        empresa = resultado.request.empresa_nome
        limpo = re.sub(r"[^\w\s-]", "", empresa, flags=re.UNICODE)
        limpo = re.sub(r"\s+", "_", limpo.strip()) or "Empresa"
        data = resultado.created_at.strftime("%Y-%m-%d")
        return f"LLMO_{limpo}_{data}.html"

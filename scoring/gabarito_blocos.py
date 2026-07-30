"""Gabarito fixo dos blocos manuais 2–6 da planilha LLMO."""

from __future__ import annotations

from typing import Any

# Estrutura: bloco_id -> metadados + critérios (id, label, como_verificar, gabarito)

BLOCOS_MANUAIS_DEFINICAO: list[dict[str, Any]] = [
    {
        "id": "bloco2",
        "numero": 2,
        "titulo": "Autoridade de conteúdo",
        "criterios": [
            {
                "id": "b2_faq",
                "label": "FAQ estruturado no site",
                "como_verificar": (
                    "Verificar se existe página /faq ou seção de perguntas "
                    "respondidas no site"
                ),
                "gabarito": (
                    "0 → Não existe nenhuma seção de perguntas\n"
                    "3 → Existe mas com menos de 5 perguntas e respostas curtas\n"
                    "5 → 5 a 9 perguntas respondidas com texto razoável\n"
                    "7 → 10+ perguntas com respostas de 2–3 parágrafos cada\n"
                    "9 → 10+ perguntas, respostas completas + palavras-chave\n"
                    "10 → Tudo acima + Schema FAQPage implementado e validado"
                ),
            },
            {
                "id": "b2_blog",
                "label": "Artigos/blog sobre procedimentos",
                "como_verificar": (
                    "Verificar seção de blog ou artigos. Ver data do último post."
                ),
                "gabarito": (
                    "0 → Não existe blog ou seção de conteúdo\n"
                    "3 → Existe mas último post tem +6 meses (desatualizado)\n"
                    "5 → Atualizado mas conteúdo genérico, sem nome de procedimentos\n"
                    "7 → Artigos com nome de procedimentos\n"
                    "9 → Artigos técnicos + menção de cidade + publicados mensalmente\n"
                    "10 → Artigos longos (+800 palavras), geolocalização, atualizados"
                ),
            },
            {
                "id": "b2_cidade",
                "label": "Conteúdo menciona cidade / bairro",
                "como_verificar": (
                    "Buscar no site palavras como cidade, bairro e estado"
                ),
                "gabarito": (
                    "0 → Cidade não é mencionada em nenhum texto do site\n"
                    "3 → Aparece só no endereço/rodapé\n"
                    "5 → Mencionado em algumas páginas de forma genérica\n"
                    "7 → Presente no corpo de textos relevantes\n"
                    "9 → Cidade + bairro + contexto no texto\n"
                    "10 → Tudo acima + em títulos H1/H2 e no meta description"
                ),
            },
        ],
    },
    {
        "id": "bloco3",
        "numero": 3,
        "titulo": "Presença em diretórios e fontes externas",
        "criterios": [
            {
                "id": "b3_doctoralia",
                "label": "Doctoralia / iClinic / ZocDoc",
                "segmentos": ["medicina", "psicologia", "odontologia"],
                "como_verificar": (
                    "Buscar a empresa nos diretórios e verificar completude do perfil"
                ),
                "gabarito": (
                    "0 → Não existe perfil no diretório\n"
                    "3 → Perfil existe mas incompleto\n"
                    "5 → Perfil completo mas sem avaliações\n"
                    "7 → Perfil completo + 5 a 20 avaliações\n"
                    "9 → Perfil completo + 20+ avaliações com nota 4.5+\n"
                    "10 → Tudo acima + responde comentários + dados consistentes com GMB"
                ),
            },
            {
                "id": "b3_boaconsulta",
                "label": "Boa Consulta / Agendar.com.br",
                "segmentos": ["medicina", "psicologia", "odontologia"],
                "como_verificar": "Buscar em boaconsulta.com.br e agendar.com",
                "gabarito": (
                    "0 → Não existe perfil no diretório\n"
                    "3 → Perfil existe mas incompleto\n"
                    "5 → Perfil completo mas sem avaliações\n"
                    "7 → Perfil completo + 5 a 20 avaliações\n"
                    "9 → Perfil completo + 20+ avaliações com nota 4.5+\n"
                    "10 → Tudo acima + informações 100% consistentes com GMB"
                ),
            },
            {
                "id": "b3_mencoes",
                "label": "Menções em blogs/portais de saúde",
                "como_verificar": (
                    "Buscar no Google o nome da empresa excluindo o próprio site"
                ),
                "gabarito": (
                    "0 → Nenhuma menção encontrada em portais externos\n"
                    "3 → 1 menção em site de baixa relevância\n"
                    "5 → 1–2 menções em portais de médio porte\n"
                    "7 → 3–5 menções em portais relevantes\n"
                    "9 → 5+ menções com texto descritivo positivo\n"
                    "10 → Menção em portal de grande audiência"
                ),
            },
            {
                "id": "b3_linkedin",
                "label": "Perfil LinkedIn do profissional responsável",
                "como_verificar": (
                    "Buscar o profissional no LinkedIn — especialidade e localização"
                ),
                "gabarito": (
                    "0 → Não existe perfil no LinkedIn\n"
                    "3 → Existe mas sem especialidade ou sem cidade\n"
                    "5 → Completo com especialidade + cidade, mas sem atividade\n"
                    "7 → Completo + postagens esporádicas\n"
                    "9 → Ativo (2+/mês) com conteúdo técnico e menção da empresa\n"
                    "10 → Tudo acima + artigos ou recomendações de clientes"
                ),
            },
        ],
    },
    {
        "id": "bloco4",
        "numero": 4,
        "titulo": "Schema markup (dados estruturados)",
        "criterios": [
            {
                "id": "b4_localbusiness",
                "label": "Schema LocalBusiness implementado",
                "como_verificar": (
                    "Testar em search.google.com/test/rich-results — colar a URL do site"
                ),
                "gabarito": (
                    "0 → Nenhum schema detectado na página\n"
                    "3 → Tem schema genérico (WebPage/WebSite)\n"
                    "5 → Tem LocalBusiness mas incompleto\n"
                    "7 → LocalBusiness completo com endereço, telefone, horário e URL\n"
                    "9 → LocalBusiness completo + @type específico do segmento\n"
                    "10 → Tipos validados sem erros no Rich Results Test"
                ),
            },
            {
                "id": "b4_tipo_especifico",
                "label": "Schema @type específico (ex.: Dentist)",
                "como_verificar": (
                    "Ver código-fonte do site (Ctrl+U) e buscar '@type'"
                ),
                "gabarito": (
                    "0 → @type ausente ou somente Organization\n"
                    "3 → Tem @type genérico (LocalBusiness sem especialização)\n"
                    "6 → Tem @type específico mas incompleto\n"
                    "8 → @type específico + especialidade preenchida\n"
                    "10 → Completo + aggregateRating + sameAs com redes sociais"
                ),
            },
            {
                "id": "b4_faqpage",
                "label": "Schema FAQPage implementado",
                "como_verificar": (
                    "Verificar no Rich Results Test se aparece o item FAQ"
                ),
                "gabarito": (
                    "0 → FAQPage inexistente\n"
                    "3 → Existe mas com menos de 3 perguntas no schema\n"
                    "6 → FAQPage com 4–7 perguntas válidas\n"
                    "8 → 8–12 perguntas com respostas completas e validadas\n"
                    "10 → 10+ perguntas, sem erros, aparece como Rich Result"
                ),
            },
        ],
    },
    {
        "id": "bloco5",
        "numero": 5,
        "titulo": "Google Meu Negócio (GMB)",
        "criterios": [
            {
                "id": "b5_perfil",
                "label": "Perfil verificado e completo",
                "como_verificar": (
                    "Buscar a empresa no Google Maps e checar cada campo"
                ),
                "gabarito": (
                    "0 → Perfil não existe ou não está verificado\n"
                    "3 → Verificado mas sem fotos, horário incompleto ou categoria errada\n"
                    "5 → Campos básicos preenchidos mas sem fotos profissionais\n"
                    "7 → Completo com fotos, horário, site, telefone e categoria correta\n"
                    "9 → Tudo acima + serviços listados\n"
                    "10 → Perfil 100% completo + perguntas e respostas + atributos"
                ),
            },
            {
                "id": "b5_avaliacoes",
                "label": "Avaliações positivas (quantidade e nota)",
                "como_verificar": (
                    "Contar avaliações e verificar nota média no Google Maps"
                ),
                "gabarito": (
                    "0 → Menos de 5 avaliações\n"
                    "3 → 5 a 10 avaliações com nota abaixo de 4.0\n"
                    "5 → 11 a 20 avaliações com nota 4.0–4.4\n"
                    "7 → 21 a 50 avaliações com nota 4.5+\n"
                    "9 → 51 a 100 avaliações com nota 4.7+ e respostas\n"
                    "10 → 100+ avaliações, nota 4.8+, respostas personalizadas"
                ),
            },
            {
                "id": "b5_posts",
                "label": "Posts regulares publicados no GMB",
                "como_verificar": (
                    "Clicar em Atualizações no perfil do Google Maps"
                ),
                "gabarito": (
                    "0 → Nunca publicou nenhum post\n"
                    "3 → Publicou 1–2 posts há muito tempo (+3 meses)\n"
                    "5 → Posta esporadicamente (1x/mês ou menos)\n"
                    "7 → Posta semanalmente com foto e texto descritivo\n"
                    "9 → Posta 2–3x/semana\n"
                    "10 → Tudo acima + usa formatos oferta, evento, novidade"
                ),
            },
        ],
    },
    {
        "id": "bloco6",
        "numero": 6,
        "titulo": "Reputação digital e consistência NAP",
        "criterios": [
            {
                "id": "b6_nap",
                "label": "NAP consistente em todos os canais",
                "como_verificar": (
                    "Comparar GMB x Site x Instagram x diretórios. "
                    "Nome, endereço e telefone devem ser idênticos."
                ),
                "gabarito": (
                    "Comece com 10 e desconte 2 pontos por cada divergência:\n"
                    "─ Nome diferente entre canais → -2\n"
                    "─ Endereço diferente → -2\n"
                    "─ Telefone diferente ou ausente → -2\n"
                    "─ Horário divergente → -1\n"
                    "─ Site com URL diferente → -1"
                ),
            },
            {
                "id": "b6_respostas",
                "label": "Respostas às avaliações do Google",
                "como_verificar": (
                    "Verificar no perfil GMB se há respostas da empresa às avaliações"
                ),
                "gabarito": (
                    "0 → Nunca respondeu nenhuma avaliação\n"
                    "3 → Respondeu apenas avaliações negativas\n"
                    "5 → Responde menos da metade, com textos genéricos\n"
                    "7 → Responde a maioria com texto personalizado\n"
                    "9 → Responde todas com personalização + menção ao serviço\n"
                    "10 → Tudo acima + responde em até 24h"
                ),
            },
            {
                "id": "b6_instagram",
                "label": "Instagram com geotag e hashtags locais",
                "como_verificar": (
                    "Verificar os últimos 12 posts: localização marcada e hashtags"
                ),
                "gabarito": (
                    "0 → Nenhum post com geolocalização, sem hashtags locais\n"
                    "3 → Geotag em menos de 30% dos posts\n"
                    "5 → Geotag na maioria + algumas hashtags locais\n"
                    "7 → Geotag em todos + hashtags estratégicas da cidade\n"
                    "9 → Tudo acima + hashtags de bairro\n"
                    "10 → Geotag sempre + hashtags locais + de procedimento"
                ),
            },
        ],
    },
]


def _criterio_aplica(criterio: dict[str, Any], segmento: str | None) -> bool:
    """Critério sem 'segmentos' vale para todos; com lista, só nos segmentos indicados."""
    segs = criterio.get("segmentos")
    if not segs or segmento is None:
        return True
    return str(segmento).lower() in {s.lower() for s in segs}


def blocos_para_segmento(segmento: str | None = None) -> list[dict[str, Any]]:
    """Definição dos blocos 2–6 filtrada pelo segmento (None = todos os critérios)."""
    resultado: list[dict[str, Any]] = []
    for bloco in BLOCOS_MANUAIS_DEFINICAO:
        criterios = [c for c in bloco["criterios"] if _criterio_aplica(c, segmento)]
        if criterios:
            resultado.append({**bloco, "criterios": criterios})
    return resultado


def ids_criterios_validos(segmento: str | None = None) -> set[str]:
    return {
        c["id"]
        for bloco in blocos_para_segmento(segmento)
        for c in bloco["criterios"]
    }


def definicao_publica(segmento: str | None = None) -> list[dict[str, Any]]:
    """Payload para a UI (sem lógica de cálculo)."""
    return blocos_para_segmento(segmento)

"""Auditor técnico do site — checks SEO, LLMO e conteúdo."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _checks_vazios() -> dict[str, dict[str, bool]]:
    return {
        "seo": {
            "ssl": False,
            "meta_description": False,
            "canonical": False,
            "viewport": False,
            "sitemap": False,
            "robots": False,
            "open_graph": False,
            "h1": False,
            "conteudo_html": False,
        },
        "llmo": {
            "schema_ld": False,
            "faq_schema": False,
            "local_business": False,
            "llms_txt": False,
            "open_graph_completo": False,
        },
        "conteudo": {
            "h1_presente": False,
            "estrutura_semantica": False,
            "conteudo_substancial": False,
            "blog_ativo": False,
        },
    }


class SiteAuditor:
    USER_AGENT = "LLMO-Vertice/2.1 (+https://verticecarioca.com.br; auditor)"

    async def auditar(self, site_url: str | None) -> dict[str, Any]:
        base = _checks_vazios()
        meta: dict[str, Any] = {
            "url_final": None,
            "status_http": None,
            "erro": None,
            "tempo_ms": 0,
        }

        if not site_url:
            meta["motivo"] = "site_url_ausente"
            return {**base, "meta": meta}

        inicio = time.perf_counter()
        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers=headers,
                verify=True,
            ) as client:
                resp = await client.get(site_url)
                meta["status_http"] = resp.status_code
                meta["url_final"] = str(resp.url)
                html = resp.text
                origem = f"{resp.url.scheme}://{resp.url.host}"

                soup = BeautifulSoup(html, "lxml")
                texto = soup.get_text(" ", strip=True)

                base["seo"]["ssl"] = str(resp.url).startswith("https")
                base["seo"]["meta_description"] = bool(
                    soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
                )
                base["seo"]["canonical"] = bool(
                    soup.find("link", attrs={"rel": re.compile("canonical", re.I)})
                )
                base["seo"]["viewport"] = bool(
                    soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
                )
                og_title = soup.find("meta", property="og:title")
                og_desc = soup.find("meta", property="og:description")
                og_image = soup.find("meta", property="og:image")
                og_url = soup.find("meta", property="og:url")
                base["seo"]["open_graph"] = bool(og_title and og_desc)
                base["llmo"]["open_graph_completo"] = bool(
                    og_title and og_desc and og_image and og_url
                )

                h1s = soup.find_all("h1")
                base["seo"]["h1"] = len(h1s) >= 1
                base["conteudo"]["h1_presente"] = len(h1s) >= 1
                base["seo"]["conteudo_html"] = len(texto) > 500
                base["conteudo"]["conteudo_substancial"] = len(texto) > 3000
                base["conteudo"]["estrutura_semantica"] = bool(
                    soup.find(["main", "article", "section"]) or soup.find_all(re.compile("^h[2-6]$"))
                )
                html_lower = html.lower()
                base["conteudo"]["blog_ativo"] = bool(
                    re.search(r"/(blog|artigos|noticias)(/|\"|'|\s)", html_lower)
                )

                # JSON-LD
                schemas = []
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        schemas.append(json.loads(script.string or ""))
                    except Exception:  # noqa: BLE001
                        continue
                base["llmo"]["schema_ld"] = len(schemas) > 0
                dump = json.dumps(schemas, ensure_ascii=False).lower()
                base["llmo"]["faq_schema"] = "faqpage" in dump
                base["llmo"]["local_business"] = any(
                    t in dump
                    for t in (
                        "localbusiness",
                        "medicalbusiness",
                        "legalservice",
                        "professionalservice",
                        "physician",
                        "dentist",
                    )
                )

                robots_ok = False
                sitemap_ok = False
                try:
                    r_robots = await client.get(urljoin(origem + "/", "robots.txt"))
                    robots_ok = r_robots.status_code == 200
                    sitemap_url = urljoin(origem + "/", "sitemap.xml")
                    if robots_ok:
                        m = re.search(r"(?i)sitemap:\s*(\S+)", r_robots.text)
                        if m:
                            sitemap_url = m.group(1).strip()
                    r_sm = await client.get(sitemap_url)
                    sitemap_ok = r_sm.status_code == 200
                except Exception:  # noqa: BLE001
                    pass
                base["seo"]["robots"] = robots_ok
                base["seo"]["sitemap"] = sitemap_ok

                try:
                    r_llms = await client.get(urljoin(origem + "/", "llms.txt"))
                    base["llmo"]["llms_txt"] = r_llms.status_code == 200
                except Exception:  # noqa: BLE001
                    base["llmo"]["llms_txt"] = False

        except Exception as e:  # noqa: BLE001
            meta["erro"] = str(e)
            logger.warning("[SiteAuditor] falha em %s: %s", site_url, e)

        meta["tempo_ms"] = int((time.perf_counter() - inicio) * 1000)
        logger.info(
            "[SiteAuditor] %s | status=%s | ssl=%s | schema=%s",
            site_url,
            meta.get("status_http"),
            base["seo"]["ssl"],
            base["llmo"]["schema_ld"],
        )
        return {**base, "meta": meta}

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "cnes-continua-obrigatorio-sncr-afe-farmacias" / "index.html"
SNCR_PATH = ROOT / "noticias" / "rdc-1000-2025-anvisa-prorroga-prazo-sncr" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
ROUTE = "/noticias/cnes-continua-obrigatorio-sncr-afe-farmacias/"
URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-05-21T20:00:00-03:00"
UPDATED = "2026-09-28T07:00:07-03:00"
TITLE = "CNES continua obrigatório? Entenda a relação com o SNCR"
SNCR_TITLE = "SNCR: nova etapa começa em 30 de setembro; veja o que muda para farmácias e drogarias"
FORBIDDEN_TERMS = (
    "novo prazo",
    "acesso futuro",
    "prazo até 30/09",
    "prazo de até 30/09",
    "farmácia popular",
    "sncr-farmácia",
    "e-cnpj",
    "passo a passo",
    "garantimos",
)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _body(html):
    return re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1)


def _news_article(html):
    pattern = re.compile(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL)
    blocks = [json.loads(match.group(1)) for match in pattern.finditer(html)]
    return next(block for block in blocks if block.get("@type") == "NewsArticle")


def _related_title(html, route):
    match = re.search(
        rf'<a class="article-related-news__card" href="{re.escape(route)}">.*?'
        r'<strong class="article-related-news__title">([^<]+)</strong>',
        html,
        re.DOTALL,
    )
    assert match is not None, route
    return match.group(1)


def test_cnes_news_title_dates_and_metadata_are_synchronized():
    html = NEWS_PATH.read_text(encoding="utf-8")
    news = _news_article(html)
    description = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)

    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'<meta property="og:title" content="{TITLE}" />' in html
    assert f'<meta name="twitter:title" content="{TITLE}" />' in html
    assert re.search(r"<h1[^>]*>(.*?)</h1>", html).group(1) == TITLE
    assert news["headline"] == TITLE
    assert f'<meta property="og:description" content="{description}" />' in html
    assert f'<meta name="twitter:description" content="{description}" />' in html
    assert news["description"] == description
    assert f'<link rel="canonical" href="{URL}" />' in html
    assert news["url"] == URL

    assert news["datePublished"] == PUBLISHED
    assert news["dateModified"] == UPDATED
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{UPDATED}" />' in html
    assert f'<time datetime="{PUBLISHED}">21/05/2026</time> às 20h00' in html
    assert f'<time datetime="{UPDATED}">28/09/2026</time> às 07h00' in html


def test_cnes_news_answers_the_question_without_links_or_tutorial():
    html = NEWS_PATH.read_text(encoding="utf-8")
    body_html = _body(html)
    body = _text(body_html)

    assert "href=" not in body_html
    for term in (
        "A resposta é não",
        "AFE substituiu o CNES apenas como forma de identificar a farmácia privada dentro do SNCR",
        "dispensários públicos",
        "normas do Ministério da Saúde",
        "públicos ou privados",
        "vacinação",
        "SNGPC",
        "implementação gradual",
        "não é prazo para obter ou regularizar o CNES",
        "escopos próprios",
    ):
        assert term in body, term
    lead = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", html, re.DOTALL).group(1)
    description = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
    editorial = " ".join((TITLE, description, lead, body)).casefold()
    for term in FORBIDDEN_TERMS:
        assert term not in editorial, term


def test_cnes_card_is_unique_current_and_highlighted_in_the_listing():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)
    matches = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert html.count(f'"url":"{URL}"') == 1
    assert len(matches) == 1
    card = matches[0]
    opening = card.split(">", 1)[0]
    assert "news-card-compact" not in opening
    assert f'data-updated="{UPDATED}"' in opening
    assert f'data-title="{TITLE}"' in opening
    assert f'<time datetime="{UPDATED}" class="leading-none">28/09/2026 • 07h00</time>' in card
    summary = re.search(r'data-summary="([^"]+)"', opening).group(1)
    assert f">{summary}</p>" in card
    assert "não dispensa o CNES" in summary
    assert "Ler atualização" in card


def test_cnes_and_sncr_related_cards_use_current_titles():
    cnes_html = NEWS_PATH.read_text(encoding="utf-8")
    sncr_html = SNCR_PATH.read_text(encoding="utf-8")

    assert _related_title(cnes_html, "/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/") == SNCR_TITLE
    assert _related_title(sncr_html, ROUTE) == TITLE


def test_cnes_news_has_current_sitemap_lastmod_and_no_new_notice():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")
    comunicado = COMUNICADO_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-09-28</lastmod>" in sitemap
    assert ROUTE not in comunicado

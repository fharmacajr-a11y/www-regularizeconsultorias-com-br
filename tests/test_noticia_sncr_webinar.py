import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "rdc-1000-2025-anvisa-prorroga-prazo-sncr" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
ROUTE = "/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/"
URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-05-28T20:36:00-03:00"
UPDATED = "2026-09-21T00:03:03-03:00"
ADSENSE_SCRIPT_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
# O webinar não comprova que a operação eletrônica do SNCR já foi liberada.
FORBIDDEN_CLAIMS = (
    "já estão valendo",
    "já está valendo",
    "já liberad",
    "já está em operação",
    "já estão em operação",
    "entrou em operação",
    "entraram em operação",
    "em produção",
    "prazo foi prorrogado novamente",
    "nova prorrogação foi anunciada",
    "prazo passa de 30/09/2026",
)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _callout(html):
    start = html.index("<aside data-news-update-callout")
    return html[start:html.index("</aside>", start)]


def _news_cards(html):
    return re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)


def _active_notices(html):
    return [
        article
        for article in re.findall(r"(<article\b[^>]*>.*?</article>)", html, re.DOTALL)
        if 'data-status="resolved"' not in article.split(">", 1)[0]
    ]


def test_sncr_news_update_keeps_publication_and_adds_the_webinar_callout():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _callout(html)
    callout_text = _text(callout)

    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{UPDATED}" />' in html
    assert f'<time datetime="{UPDATED}">21/09/2026</time> às 00h03' in html
    assert f'<link rel="canonical" href="{URL}" />' in html
    assert html.count(ADSENSE_SCRIPT_MARKER) == 1
    assert html.count("data-news-update-callout") - html.count("[data-news-update-callout]") == 1

    assert "ATUALIZAÇÃO" in callout_text
    for term in (
        "17/09/2026 já foi realizado",
        "gravação e a apresentação",
        "21/09/2026, às 15h",
        "webinar on-line",
        "aberto ao público geral",
        "não exige cadastro prévio",
        "foco especial em farmácias e drogarias",
        "estabelecimentos dispensadores",
        "não modifica o prazo",
        "não informa nova prorrogação",
        "antecipação da entrada em operação",
        "30/09/2026",
        "Versão 2",
        "18/05/2026",
    ):
        assert term in callout_text
    assert "href=" not in callout


def test_sncr_news_makes_no_claim_that_electronic_operation_is_already_released():
    for path in (NEWS_PATH, COMUNICADO_PATH):
        text = _text(path.read_text(encoding="utf-8")).casefold()
        for claim in FORBIDDEN_CLAIMS:
            assert claim not in text, (path.relative_to(ROOT), claim)

    html = NEWS_PATH.read_text(encoding="utf-8")
    assert "teams.microsoft.com" not in html
    assert "youtube.com" not in html


def test_sncr_card_is_unique_current_and_featured_in_the_news_listing():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = _news_cards(html)
    sncr_cards = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert len(sncr_cards) == 1
    card = sncr_cards[0]
    assert cards.index(card) == 2
    assert "news-card-compact" not in card.split(">", 1)[0]
    assert f'data-updated="{UPDATED}"' in card
    assert f'<time datetime="{UPDATED}" class="leading-none">21/09/2026 • 00h03</time>' in card
    for term in ("21/09", "15h", "farmácias e drogarias", "17/09", "gravação e apresentação", "30/09/2026"):
        assert term in card


def test_comunicado_keeps_one_sncr_card_and_six_active_notices():
    html = COMUNICADO_PATH.read_text(encoding="utf-8")
    active = _active_notices(html)
    sncr_cards = [article for article in active if 'data-category="sncr"' in article]

    assert html.count('data-category="sncr"') == 1
    assert html.count(f'href="{ROUTE}"') == 1
    assert len(active) == 6
    assert re.findall(r'class="aviso-badge[^"]*">(\d+)</span>', html) == ["6", "6"]
    assert len(sncr_cards) == 1
    card_text = _text(sncr_cards[0])
    for term in (
        "21/09/2026, às 15h",
        "farmácias e drogarias",
        "estabelecimentos dispensadores",
        "17/09 já foi realizado",
        "gravação e apresentação disponíveis",
        "30/09/2026",
        "Versão 2",
        "18/05/2026",
        "Ver atualização SNCR",
    ):
        assert term in card_text
    assert active[0] is sncr_cards[0]


def test_sncr_news_has_current_sitemap_lastmod():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-09-21</lastmod>" in sitemap

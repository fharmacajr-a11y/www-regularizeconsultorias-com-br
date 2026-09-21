import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[1]
SLUG = "cnes-competencia-09-2026-prazo-transmissao"
ROUTE = f"/noticias/{SLUG}/"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
PREVIOUS_PATH = ROOT / "noticias" / "cnes-competencia-08-2026-prazo-transmissao" / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-09-14T13:31:27-03:00"
TITLE = "CNES abre competência 09/2026 com envio até 7 de outubro"
# OG temporária: fallback genérico de notícias por decisão editorial, até existir a OG específica.
GENERIC_OG_PATH = ROOT / "assets" / "img" / "og" / "noticias.jpg"
GENERIC_OG_URL = "https://www.regularizeconsultorias.com.br/assets/img/og/noticias.jpg"
ADSENSE_SRC = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2993532924249779"
# A abertura da competência não confirma versão nova do CNES Desktop.
VERSION_CLAIMS = (
    "nova versão foi",
    "nova versão do cnes desktop foi",
    "nova versão obrigatória",
    "versão obrigatória",
    "desktop 09/2026 disponível",
    "está disponível a versão",
    "foi disponibilizada a versão",
    "scnes 4.",
    "prorrog",
)


def _html():
    return PAGE_PATH.read_text(encoding="utf-8")


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _body(html):
    start = html.index('<section class="article-body">')
    return _text(html[start:html.index("</section>", start)])


def _news_article(html):
    schemas = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
    return [item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle"]


def test_page_identity_dates_and_newsarticle():
    html = _html()
    news = _news_article(html)

    assert f'<link rel="canonical" href="{PUBLIC_URL}" />' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}" />' in html
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert html.count("<h1") == 1 and f">{TITLE}</h1>" in html
    assert len(news) == 1
    assert news[0]["headline"] == TITLE
    assert news[0]["url"] == PUBLIC_URL
    assert news[0]["articleSection"] == "CNES"
    assert news[0]["datePublished"] == news[0]["dateModified"] == PUBLISHED
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{PUBLISHED}" />' in html
    assert "Atualizado em" not in html
    assert f'<time datetime="{PUBLISHED}">14/09/2026</time> às 13h31' in html
    assert 'bg-amber-500 px-2.5 py-1 text-white whitespace-nowrap">Atualização</span>' in html


def test_transmission_window_and_schedule_dates():
    body = _body(_html())

    assert "competência 09/2026" in body
    assert "Em informe publicado em 14 de setembro de 2026" in body
    assert "Módulo Transmissor" in body
    assert "14/09/2026 a 07/10/2026" in body
    assert "aberto em 14/09/2026, com encerramento informado em 07/10/2026" in body
    assert "14/10/2026 para a disponibilização do TXT definitivo" in body
    assert "30/10/2026 como data limite de envio da remessa do SIA/SIH" in body
    assert "08/09/2026" not in body and "13/08/2026" not in body


def test_competence_is_not_presented_as_a_new_desktop_version():
    html = _html()
    body = _body(html)
    # Head, hero e corpo; a seção de notícias relacionadas cita legitimamente a prorrogação de 06/2026.
    editorial = html.split('<section class="article-important-notice', 1)[0]
    lowered = _text(editorial).casefold()

    assert "não significa, por si só, que uma nova versão do CNES Desktop tenha sido publicada" in body
    assert "data de referência" in body
    assert "se houver versão para a competência, será colocado aviso no site com antecedência" in body
    assert "O informe de 14/09/2026 trata apenas da abertura do Módulo Transmissor" in body
    for claim in VERSION_CLAIMS:
        assert claim not in lowered, claim
    assert not re.search(r"\b4\.8\.\d+\b", html)


def test_temporary_generic_og_is_used_and_valid():
    html = _html()

    assert html.count(f'<meta property="og:image" content="{GENERIC_OG_URL}" />') == 1
    assert html.count(f'<meta property="og:image:secure_url" content="{GENERIC_OG_URL}" />') == 1
    assert html.count(f'<meta name="twitter:image" content="{GENERIC_OG_URL}" />') == 1
    assert _news_article(html)[0]["image"] == GENERIC_OG_URL
    assert f"{SLUG}.webp" not in html
    assert "cnes-competencia-08-2026-prazo-transmissao.webp" not in html
    assert not (ROOT / "assets" / "img" / "og" / "noticias" / f"{SLUG}.webp").exists()
    with Image.open(GENERIC_OG_PATH) as image:
        assert image.format == "JPEG"
        assert image.size == (1200, 630)
        image.verify()


def test_canonical_adsense_snippet_exactly_once_in_head():
    html = _html()
    head = html.split("</head>", 1)[0]

    assert html.count("adsbygoogle.js") == 1
    assert head.count(f'<script async src="{ADSENSE_SRC}"\n     crossorigin="anonymous"></script>') == 1
    assert "<ins" not in html and "data-ad-slot" not in html


def test_previous_competence_remains_a_historical_record():
    previous = PREVIOUS_PATH.read_text(encoding="utf-8")

    assert "CNES abre competência 08/2026 com transmissão prevista até 8 de setembro" in previous
    assert '"datePublished":"2026-08-14T14:42:53-03:00","dateModified":"2026-08-14T14:42:53-03:00"' in previous
    assert "13/08/2026 a 08/09/2026" in previous
    assert "competência 09/2026" not in previous
    assert "cnes-competencia-09-2026" not in previous
    assert f'href="/noticias/cnes-competencia-08-2026-prazo-transmissao/"' in _html()


def test_news_index_has_one_card_and_one_itemlist_entry():
    html = INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", html, re.DOTALL)
    own = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    assert len(own) == 1
    assert 'data-category="cnes"' in own[0]
    assert f'data-updated="{PUBLISHED}"' in own[0]
    assert f'<time datetime="{PUBLISHED}" class="leading-none">14/09/2026 • 13h31</time>' in own[0]
    assert ">Atualização</span>" in own[0] and "Ler atualização" in own[0]
    assert len(cards) == 80
    assert '<span>CNES</span><span class="text-xs text-slate-400">5</span>' in html


def test_sitemap_lists_the_new_url_once():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert f"<loc>{PUBLIC_URL}</loc>\n    <lastmod>2026-09-14</lastmod>" in sitemap

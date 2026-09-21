import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[1]
SLUG = "anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis"
ROUTE = f"/noticias/{SLUG}/"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-09-14T12:20:35-03:00"
TITLE = "Anvisa convoca estabelecimentos com AFE para preparações estéreis"
# OG temporária: fallback genérico de notícias por decisão editorial, até existir a OG específica.
GENERIC_OG_PATH = ROOT / "assets" / "img" / "og" / "noticias.jpg"
GENERIC_OG_URL = "https://www.regularizeconsultorias.com.br/assets/img/og/noticias.jpg"
FUTURE_OG_NAME = f"{SLUG}.webp"
ADSENSE_SRC = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2993532924249779"
PROMISES = (
    "garante aprovação",
    "garantimos",
    "aprovação garantida",
    "deferimento garantido",
    "deferimento automático",
    "será deferid",
    "regularize imediatamente",
    "sua afe será cancelada",
    "todas as farmácias devem",
    "todos os estabelecimentos devem protocolar",
)


def _html():
    return PAGE_PATH.read_text(encoding="utf-8")


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _body(html):
    start = html.index('<section class="article-body">')
    return html[start:html.index("</section>", start)]


def _news_article(html):
    schemas = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
    return [item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle"]


def test_page_identity_metadata_and_newsarticle():
    html = _html()
    news = _news_article(html)

    assert f'<link rel="canonical" href="{PUBLIC_URL}" />' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}" />' in html
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert html.count("<h1") == 1 and f">{TITLE}</h1>" in html
    assert len(news) == 1
    assert news[0]["headline"] == TITLE
    assert news[0]["url"] == PUBLIC_URL
    assert news[0]["datePublished"] == PUBLISHED
    assert news[0]["dateModified"] == PUBLISHED
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{PUBLISHED}" />' in html
    assert "Atualizado em" not in html
    assert f'<time datetime="{PUBLISHED}">14/09/2026</time> às 12h20' in html


def test_official_facts_of_the_edital_are_preserved():
    body = _text(_body(_html()))

    for term in (
        "Edital de Chamamento nº 6/2026",
        "08/09/2026",
        "07/10/2026",
        "30 dias corridos",
        "um dia útil após a publicação do edital",
        "25351.925832/2026-29",
        "GGFIS",
        "manipulação de preparações estéreis",
        "atualização voluntária dos dados cadastrais e regulatórios",
        "atividades autorizadas correspondem àquelas efetivamente exercidas",
        "fiscalização e inspeção sanitária",
        "monitoramento de risco sanitário",
    ):
        assert term in body, term


def test_subject_7112_is_restricted_to_excluding_an_activity_not_exercised():
    body = _text(_body(_html()))

    assert "7112 – AFE – Alteração – Farmácias e Drogarias – Redução de Atividades" in body
    assert "mas não exerce efetivamente essa atividade" in body
    assert "excluir a atividade de manipulação de preparações estéreis do escopo da AFE" in body
    assert "O 7112 não é um procedimento comum a todos os estabelecimentos alcançados pelo chamamento" in body
    assert "não deve ser lido como caminho para inclusão de atividade, concessão ou renovação de AFE" in body
    # O código não pode aparecer associado a outros usos.
    for sentence in re.split(r"(?<=[.!?])\s+", body):
        if "7112" in sentence:
            lowered = sentence.casefold()
            assert any(
                marker in lowered
                for marker in (
                    "redução de atividades",
                    "não é um procedimento comum",
                    "não a exerce",
                    "não exerce",
                    "não é exercida",
                )
            ), sentence


def test_page_makes_no_promise_of_approval_or_generic_obligation():
    text = _text(_html()).casefold()

    for promise in PROMISES:
        assert promise not in text, promise
    assert "fonte oficial" not in text
    assert "gov.br/anvisa" not in _html()
    assert "anvisalegis.datalegis.net" not in _html()


def test_temporary_generic_og_is_used_and_valid():
    html = _html()

    assert html.count(f'<meta property="og:image" content="{GENERIC_OG_URL}" />') == 1
    assert html.count(f'<meta name="twitter:image" content="{GENERIC_OG_URL}" />') == 1
    assert _news_article(html)[0]["image"] == GENERIC_OG_URL
    assert '<meta property="og:image:type" content="image/jpeg" />' in html
    assert FUTURE_OG_NAME not in html
    assert not (ROOT / "assets" / "img" / "og" / "noticias" / FUTURE_OG_NAME).exists()
    with Image.open(GENERIC_OG_PATH) as image:
        assert image.format == "JPEG"
        assert image.size == (1200, 630)
        image.verify()


def test_canonical_adsense_snippet_exactly_once_in_head():
    html = _html()
    head = html.split("</head>", 1)[0]

    assert html.count("adsbygoogle.js") == 1
    assert head.count(f'<script async src="{ADSENSE_SRC}"') == 1
    assert 'crossorigin="anonymous"></script>' in head
    assert "<ins" not in html and "data-ad-slot" not in html


def test_news_index_has_one_card_and_one_itemlist_entry():
    html = INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", html, re.DOTALL)
    own = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    assert len(own) == 1
    assert f'data-updated="{PUBLISHED}"' in own[0]
    assert f'<time datetime="{PUBLISHED}" class="leading-none">14/09/2026 • 12h20</time>' in own[0]
    assert ">Atualização</span>" in own[0] and "Ler atualização" in own[0]
    assert len(cards) == 80


def test_sitemap_lists_the_new_url_once():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert f"<loc>{PUBLIC_URL}</loc>\n    <lastmod>2026-09-14</lastmod>" in sitemap

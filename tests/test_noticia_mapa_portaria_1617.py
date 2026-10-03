import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
COMUNICADO = ROOT / "comunicado" / "index.html"
SLUG = "mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal"
ARTICLE = ROOT / "noticias" / SLUG / "index.html"
DRAFT = ROOT / "noticias" / "a-publicar" / SLUG / "index.html"
TITLE = "MAPA restringe antimicrobianos em aditivos para alimentação animal"
DESCRIPTION = (
    "A Portaria SDA/MAPA nº 1.617/2026 já está vigente e restringe aditivos "
    "com antimicrobianos na alimentação animal. O tratamento dos estoques depende do caso."
)
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
STAMP = "2026-10-03T00:33:00-03:00"
SOURCES = (
    "https://www.in.gov.br/en/web/dou/-/portaria-sda/mapa-n-1.617-de-24-de-abril-de-2026-701457881",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/copy_of_PORTARIASDA_MAPAN1.617DE24DEABRILDE2026PORTARIASDA_MAPAN1.617DE24DEABRILDE2026DOUImprensaNacional.pdf",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/SEI_52249020_Oficio_Circular_29.pdf",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/legislacao-alimentacao-animal",
)


class _JsonLd(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script" and dict(attrs).get("type") == "application/ld+json":
            self._current = []

    def handle_data(self, data):
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._current is not None:
            self.blocks.append("".join(self._current))
            self._current = None


def _jsonld(html):
    parser = _JsonLd()
    parser.feed(html)
    return [json.loads(block) for block in parser.blocks]


def _cards(html):
    return re.findall(
        r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)",
        html,
        re.DOTALL,
    )


def test_portaria_1617_is_published_at_the_public_url():
    html = ARTICLE.read_text(encoding="utf-8")

    assert ARTICLE.is_file()
    assert not DRAFT.exists()
    assert not (ROOT / "noticias" / "a-publicar").exists()
    assert "a-publicar" not in html
    assert "noindex" not in html.casefold()
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert "<h1 class=" in html and TITLE in html
    assert "article-badge-informativo" in html
    assert ">Informativo<" in html
    assert "category-chip--mapa" in html
    assert ">M.A.P.A<" in html
    assert f'<link rel="canonical" href="{PUBLIC_URL}" />' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}" />' in html
    assert f'<meta property="article:published_time" content="{STAMP}" />' in html
    assert f'<meta property="article:modified_time" content="{STAMP}" />' in html
    assert f'<time datetime="{STAMP}">03/10/2026</time> às 00h33' in html
    assert "Atualizado em" not in html
    assert html.count("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js") == 1
    assert "adsbygoogle.push" not in html

    blocks = _jsonld(html)
    article = next(block for block in blocks if block["@type"] == "NewsArticle")
    assert article["headline"] == TITLE
    assert article["description"] == DESCRIPTION
    assert article["datePublished"] == STAMP
    assert article["dateModified"] == STAMP
    assert article["url"] == PUBLIC_URL
    assert article["articleSection"] == "M.A.P.A"
    assert article["author"]["name"] == "Júnior Costa"
    assert article["publisher"]["name"] == "Regularize Consultoria"
    assert article["mainEntityOfPage"]["@id"] == PUBLIC_URL

    breadcrumb = next(block for block in blocks if block["@type"] == "BreadcrumbList")
    third = breadcrumb["itemListElement"][2]
    assert third["position"] == 3
    assert third["name"] == "Aditivos com antimicrobianos"
    assert third["item"] == PUBLIC_URL

    assert "<h2>Fontes oficiais</h2>" not in html
    for source in SOURCES:
        assert source not in html
    assert "Aviso institucional" in html
    assert "Precisa avaliar a situação regulatória no MAPA?" in html
    assert "análise regulatória" in html or "situação regulatória" in html
    assert "SIPEAGRO" in html
    for fact in (
        "24 de abril de 2026",
        "27/04/2026",
        "23/10/2026",
        "21/01/2027",
        "Ofício-Circular nº 29/2026",
        "Diário Oficial da União",
        "edição 77",
        "avoparcina",
        "bacitracina de zinco",
        "bacitracina metileno disalicilato",
        "virginiamicina",
    ):
        assert fact in html

    folded = html.casefold()
    for forbidden in (
        "todos os produtos",
        "prazo de transição vai até outubro",
        "prazo geral",
        "qualquer produto",
        "todas as empresas",
        "passo a passo",
        "como recolher",
        "como preencher",
        "como formular",
        "substituir o antimicrobiano",
        "como solicitar",
        "como inutilizar",
        "como reformular",
    ):
        assert forbidden not in folded
    assert "Sistema Eletrônico de Informações" not in html

    href = re.search(r'href="(/whatsapp/\?text=[^"]+)"', html).group(1)
    message = unquote(parse_qs(urlsplit(href).query)["text"][0])
    assert message.startswith("Olá!")
    assert "(19) 99627-5900" in html


def test_portaria_1617_enters_the_public_listing_itemlist_and_sitemap():
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    comunicado = COMUNICADO.read_text(encoding="utf-8")
    cards = _cards(index)

    assert "a-publicar" not in index
    assert "a-publicar" not in sitemap
    assert SLUG not in comunicado
    assert "1.617" not in comunicado
    assert len(cards) == 83
    assert index.count("data-news-card") == 83
    assert "83 notícias encontradas" in index
    assert '>Todos</span><span class="text-xs text-slate-400">83<' in index
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in index
    assert '>M.A.P.A</span><span class="text-xs text-slate-400">3<' in index
    assert len(re.findall(r'\bdata-category="mapa"', index)) == 3

    card = cards[0]
    opening = card.split(">", 1)[0]
    assert f'href="/noticias/{SLUG}/"' in card
    assert index.count(f'href="/noticias/{SLUG}/"') == 1
    assert "news-card-compact" not in opening
    assert 'data-category="mapa"' in opening
    assert f'data-updated="{STAMP}"' in opening
    assert f'data-title="{TITLE}"' in opening
    assert f'data-summary="{DESCRIPTION}"' in opening
    assert ">Informativo<" in card
    assert ">M.A.P.A<" in card
    assert f'<time datetime="{STAMP}" class="leading-none">03/10/2026 • 00h33</time>' in card
    assert all("news-card-compact" not in item.split(">", 1)[0] for item in cards[:5])
    assert "news-card-compact" in cards[5].split(">", 1)[0]
    assert "nova-regra-anvisa-cnes-receitas-farmacias" in cards[5]

    collection = next(block for block in _jsonld(index) if block.get("@type") == "CollectionPage")
    items = collection["mainEntity"]["itemListElement"]
    assert len(items) == 83
    assert items[0]["position"] == 1
    assert items[0]["url"] == PUBLIC_URL
    assert [item["position"] for item in items] == list(range(1, 84))
    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert f"<loc>{PUBLIC_URL}</loc>\n    <lastmod>2026-10-03</lastmod>" in sitemap
    assert (
        "<loc>https://www.regularizeconsultorias.com.br/noticias/</loc>\n"
        "    <lastmod>2026-10-03</lastmod>"
    ) in sitemap

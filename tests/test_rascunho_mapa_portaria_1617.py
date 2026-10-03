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
DRAFT = ROOT / "noticias" / "a-publicar" / SLUG / "index.html"
PUBLIC_ARTICLE = ROOT / "noticias" / SLUG / "index.html"
TITLE = "MAPA restringe antimicrobianos em aditivos para alimentação animal"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"


def test_portaria_1617_draft_stays_out_of_public_surfaces():
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    comunicado = COMUNICADO.read_text(encoding="utf-8")

    assert DRAFT.is_file()
    assert not PUBLIC_ARTICLE.exists()
    assert SLUG not in index
    assert SLUG not in sitemap
    assert "a-publicar" not in index
    assert "a-publicar" not in sitemap
    assert "1.617" not in comunicado
    assert "Portaria SDA/MAPA" not in comunicado
    assert index.count("data-news-card") == 82
    assert '>Todos</span><span class="text-xs text-slate-400">82<' in index
    assert len(re.findall(r'\bdata-category="mapa"', index)) == 2
    assert re.search(
        r'data-news-category="mapa"[^>]*>.*?<span[^>]*>2</span>',
        index,
        re.DOTALL,
    )


def test_portaria_1617_draft_keeps_the_approved_prepublication_copy():
    draft = DRAFT.read_text(encoding="utf-8")

    assert 'name="robots" content="noindex, nofollow"' in draft
    assert 'rel="canonical"' not in draft
    assert "og:url" not in draft
    assert "mainEntityOfPage" not in draft
    assert "a-publicar" not in draft
    assert PUBLIC_URL not in draft
    assert TITLE in draft
    assert f"<h1" in draft and TITLE in draft
    assert "article-badge-informativo" in draft
    assert "Informativo" in draft
    assert "category-chip--mapa" in draft
    assert ">M.A.P.A<" in draft
    assert "Precisa avaliar a situação regulatória no MAPA?" in draft
    assert "site-regulatory-banner" in draft
    for source in (
        "https://www.in.gov.br/en/web/dou/-/portaria-sda/mapa-n-1.617-de-24-de-abril-de-2026-701457881",
        "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/copy_of_PORTARIASDA_MAPAN1.617DE24DEABRILDE2026PORTARIASDA_MAPAN1.617DE24DEABRILDE2026DOUImprensaNacional.pdf",
        "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/SEI_52249020_Oficio_Circular_29.pdf",
        "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/legislacao-alimentacao-animal",
    ):
        assert source in draft
    assert "23/10/2026" in draft
    assert "21/01/2027" in draft
    assert "27/04/2026" in draft
    folded = draft.casefold()
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
    ):
        assert forbidden not in folded
    assert "Sistema Eletrônico de Informações" not in draft

    href = re.search(r'href="(/whatsapp/\?text=[^"]+)"', draft).group(1)
    message = unquote(parse_qs(urlsplit(href).query)["text"][0])
    assert message.startswith("Olá!")

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

    parser = _JsonLd()
    parser.feed(draft)
    assert len(parser.blocks) == 2
    for block in parser.blocks:
        json.loads(block)

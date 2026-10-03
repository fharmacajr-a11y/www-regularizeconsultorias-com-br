import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ARTICLE = ROOT / "noticias" / "anvisa-atualiza-listas-substancias-cosmeticos" / "index.html"
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"
UPDATED = "2026-10-02T21:50:00-03:00"
PUBLISHED = "2026-07-05T17:00:00-03:00"


def _cards(html):
    return re.findall(
        r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>",
        html,
        re.DOTALL,
    )


def test_cp_1399_is_recorded_as_closed_on_the_existing_article():
    html = ARTICLE.read_text(encoding="utf-8")

    for banned in ("permanece aberta", "prazo permanece vigente", "recebe contribuições"):
        assert banned not in html
    assert "08/07/2026 a 08/09/2026" in html
    assert "está encerrada" in html
    assert "não alterou a lista vigente" in html
    assert "não informa prorrogação" in html
    assert "Eventual norma posterior deve ser acompanhada separadamente." in html
    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert f'content="{UPDATED}" property="article:modified_time"' in html
    assert f'<time datetime="{PUBLISHED}">05/07/2026</time> às 17h00' in html
    assert f'<time datetime="{UPDATED}">02/10/2026</time> às 21h50' in html


def test_listing_places_the_updated_cosmetics_card_second():
    html = INDEX.read_text(encoding="utf-8")
    cards = _cards(html)
    card = cards[1]

    assert len(cards) == 83
    assert "/noticias/anvisa-atualiza-listas-substancias-cosmeticos/" in card
    assert f'data-updated="{UPDATED}"' in card
    assert "está encerrada" in card
    assert "recebe contribuições" not in card
    assert "permanece aberta" not in card
    assert '>Todos</span><span class="text-xs text-slate-400">83<' in html
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in html
    assert (
        '"position":2,"url":"https://www.regularizeconsultorias.com.br'
        '/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"'
    ) in html
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-02</lastmod>" in sitemap

import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[1]
SLUG = "anvisa-revisao-propaganda-medicamentos-alimentos"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
OG_PATH = ROOT / "assets" / "img" / "og" / "noticias" / f"{SLUG}.webp"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
def _page_html():
    return PAGE_PATH.read_text(encoding="utf-8")


def test_page_distinguishes_process_opening_from_new_rules():
    html = _page_html()
    required = (
        "abertura de processos administrativos de regulação",
        "não significa que novas regras de propaganda já estejam em vigor",
        "RDC 96/2008",
        "RDC 24/2010",
        "comércio eletrônico",
        "redes sociais",
        "marketing de influenciadores",
        "marketplaces",
        "A responsabilidade regulatória não desaparece",
        "ADI) 7.788",
    )
    assert all(text in html for text in required)
    assert "Não há, na notícia oficial, definição de texto futuro, consulta pública" in html
    assert "Fonte oficial:" not in html
    assert "gov.br/anvisa" not in html


def test_page_metadata_and_newsarticle_schema_are_consistent():
    html = _page_html()
    assert f'<link rel="canonical" href="{PUBLIC_URL}"' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}"' in html
    assert f"/assets/img/og/noticias/{SLUG}.webp" in html
    assert '<meta property="og:image:width" content="1200"' in html
    assert '<meta property="og:image:height" content="630"' in html

    schemas = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    news = next(item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle")
    assert news["url"] == PUBLIC_URL
    assert news["datePublished"] == "2026-08-05T13:53:00-03:00"
    assert news["dateModified"] == "2026-08-05T13:53:00-03:00"


def test_og_asset_uses_the_project_dimensions():
    with Image.open(OG_PATH) as image:
        assert image.size == (1200, 630)
        assert image.format == "WEBP"


def test_news_index_contains_one_dated_card_and_one_itemlist_entry():
    html = INDEX_PATH.read_text(encoding="utf-8")
    assert html.count(f'href="/noticias/{SLUG}/"') == 1
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    card = re.search(
        rf'<article\b[^>]*data-news-card[^>]*>.*?href="/noticias/{SLUG}/".*?</article>',
        html,
        re.DOTALL,
    )
    assert card is not None
    assert 'datetime="2026-08-05T13:53:00-03:00"' in card.group(0)

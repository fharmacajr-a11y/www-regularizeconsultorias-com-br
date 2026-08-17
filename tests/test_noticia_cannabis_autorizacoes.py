import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[1]
SLUG = "anvisa-novas-regras-cannabis-autorizacao-especial"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
OG_PATH = ROOT / "assets" / "img" / "og" / "noticias" / f"{SLUG}.webp"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
UPDATED_AT = "2026-08-17T09:23:45-03:00"


def _page_html():
    return PAGE_PATH.read_text(encoding="utf-8")


def test_cannabis_update_covers_rdc_1015_and_past_deadline():
    html = _page_html()
    required = (
        "RDC 1.015/2026",
        "Autorização Sanitária: atenção à RDC 1.015/2026",
        "entrou em vigor em <strong>4 de maio de 2026</strong>",
        "adequações necessárias de produtos já autorizados",
        "O prazo informado para o protocolo dessas adequações foi 1º de agosto de 2026.",
        "Como essa data já passou",
    )
    assert all(text in html for text in required)
    assert "têm até 1º de agosto" not in html
    assert "prorrogação" in html
    assert "regularização automática" in html


def test_ae_and_autorizacao_sanitaria_are_explicitly_separated():
    html = _page_html()
    required = (
        "AE e Autorização Sanitária não são a mesma coisa",
        "Possuir AE não significa possuir Autorização Sanitária",
        "Autorização Sanitária não substitui automaticamente a AE",
        "O protocolo de uma não concede a outra",
        "atividade, da empresa, do produto, da finalidade e da norma aplicável",
    )
    assert all(text in html for text in required)


def test_metadata_preserves_publication_and_records_update():
    html = _page_html()
    assert f'<link href="{PUBLIC_URL}" rel="canonical"/>' in html
    assert "gov.br/anvisa" not in html
    assert "Fonte oficial" not in html
    assert "Saiba mais" not in html

    schemas = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    news = next(item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle")
    assert news["datePublished"] == "2026-08-04T08:06:00-03:00"
    assert news["dateModified"] == UPDATED_AT
    assert news["url"] == PUBLIC_URL


def test_existing_card_is_updated_once_without_changing_total():
    html = INDEX_PATH.read_text(encoding="utf-8")
    assert html.count(f'href="/noticias/{SLUG}/"') == 1
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    assert html.count("data-news-card") == 76
    assert "76 notícias encontradas" in html
    card = re.search(
        rf'<article\b[^>]*data-news-card[^>]*>.*?href="/noticias/{SLUG}/".*?</article>',
        html,
        re.DOTALL,
    )
    assert card is not None
    assert f'data-updated="{UPDATED_AT}"' in card.group(0)
    assert f'<time datetime="{UPDATED_AT}" class="leading-none">17/08/2026 • 09h23</time>' in card.group(0)
    assert "04/08/2026 • 08h06" not in card.group(0)
    assert "RDC 1.015" in card.group(0)


def test_og_and_sitemap_entry_are_preserved_and_updated():
    with Image.open(OG_PATH) as image:
        assert image.size == (1200, 630)
        assert image.format == "WEBP"
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"<url>\s*<loc>{re.escape(PUBLIC_URL)}</loc>\s*<lastmod>([^<]+)</lastmod>",
        sitemap,
    )
    assert match is not None
    assert match.group(1) == "2026-08-17"
